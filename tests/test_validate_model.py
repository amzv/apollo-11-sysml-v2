import os
import sys
import json
import logging
import pytest
from unittest.mock import MagicMock, patch

# Ensure scripts directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import validate_model
from validate_model import (
    SysMLDependencyResolver,
    SysMLKernelValidator,
    NotebookGenerator,
    FileResult,
    VizResult,
    ValidationReport,
    find_defining_package,
    run_validation,
)

# Configure logging for test output
logging.basicConfig(level=logging.INFO)

# Check if SysML kernel is installed in the test environment
try:
    import jupyter_client
    jupyter_client.kernelspec.KernelSpecManager().get_kernel_spec("sysml")
    HAS_SYSML_KERNEL = True
except Exception:
    HAS_SYSML_KERNEL = False

# ===========================================================================
# 1. SysMLDependencyResolver Tests
# ===========================================================================

def test_dependency_resolver_load_meta_index(tmp_path):
    # Create mock .meta.json
    meta_content = {
        "index": {
            "PkgA": "dirA/PkgA.sysml",
            "PkgB": "dirB/PkgB.sysml"
        }
    }
    meta_file = tmp_path / ".meta.json"
    meta_file.write_text(json.dumps(meta_content), encoding="utf-8")

    resolver = SysMLDependencyResolver(str(tmp_path))
    assert resolver.package_index == meta_content["index"]


def test_dependency_resolver_discover_packages(tmp_path):
    # Create dummy .sysml files
    dir_a = tmp_path / "dirA"
    dir_a.mkdir()
    (dir_a / "PkgA.sysml").write_text("package PkgA {}", encoding="utf-8")
    
    dir_b = tmp_path / "dirB"
    dir_b.mkdir()
    (dir_b / "PkgB.sysml").write_text("package PkgB {}", encoding="utf-8")

    # Instantiate resolver without .meta.json; should fall back to discovery
    resolver = SysMLDependencyResolver(str(tmp_path))
    resolver._discover_packages()

    assert "PkgA" in resolver.package_index
    assert "PkgB" in resolver.package_index
    # The discovered relative path should be correct
    assert resolver.package_index["PkgA"].replace("\\", "/") == "dirA/PkgA.sysml"


def test_dependency_resolver_get_imports(tmp_path):
    file_path = tmp_path / "TestPkg.sysml"
    file_path.write_text(
        "package TestPkg {\n"
        "    import PkgA;\n"
        "    private import PkgB::*;\n"
        "    import PkgC::element;\n"
        "    import PkgA; // duplicate\n"
        "}",
        encoding="utf-8"
    )

    resolver = SysMLDependencyResolver(str(tmp_path))
    imports = resolver.get_imports(str(file_path))
    assert imports == ["PkgA", "PkgB", "PkgC"]


def test_dependency_resolver_topological_sort():
    resolver = SysMLDependencyResolver(".")
    # Set up dependency graph manually
    # PkgC depends on PkgB. PkgB depends on PkgA. PkgA has no dependencies.
    resolver.dep_graph = {
        "PkgC": {"PkgB"},
        "PkgB": {"PkgA"},
        "PkgA": set()
    }
    
    order = resolver.topological_sort()
    assert order == ["PkgA", "PkgB", "PkgC"]


def test_dependency_resolver_circular_dependency():
    resolver = SysMLDependencyResolver(".")
    # PkgA depends on PkgB, and PkgB depends on PkgA (circular)
    resolver.dep_graph = {
        "PkgA": {"PkgB"},
        "PkgB": {"PkgA"}
    }
    
    # Kahns should handle gracefully and log error, but still return all nodes
    order = resolver.topological_sort()
    assert set(order) == {"PkgA", "PkgB"}


def test_dependency_resolver_resolve(tmp_path):
    # Write metadata index
    meta_content = {
        "index": {
            "PkgA": "PkgA.sysml",
            "PkgB": "PkgB.sysml"
        }
    }
    (tmp_path / ".meta.json").write_text(json.dumps(meta_content), encoding="utf-8")
    
    # Write files
    (tmp_path / "PkgA.sysml").write_text("package PkgA {}", encoding="utf-8")
    (tmp_path / "PkgB.sysml").write_text("package PkgB { import PkgA::*; }", encoding="utf-8")

    resolver = SysMLDependencyResolver(str(tmp_path))
    resolved = resolver.resolve()

    assert len(resolved) == 2
    assert resolved[0][0] == "PkgA"
    assert resolved[1][0] == "PkgB"
    assert os.path.exists(resolved[0][1])
    assert os.path.exists(resolved[1][1])


# ===========================================================================
# 2. SysMLKernelValidator Unit Tests (Mocked Kernel)
# ===========================================================================

@patch("jupyter_client.KernelManager")
def test_kernel_validator_start_shutdown(mock_km_class):
    mock_km = MagicMock()
    mock_kc = MagicMock()
    mock_km_class.return_value = mock_km
    mock_km.client.return_value = mock_kc

    validator = SysMLKernelValidator(startup_timeout=5)
    validator.start_kernel()
    
    assert validator.km == mock_km
    assert validator.kc == mock_kc
    mock_km.start_kernel.assert_called_once()
    mock_kc.wait_for_ready.assert_called_once_with(timeout=5)

    validator.shutdown_kernel()
    mock_kc.stop_channels.assert_called_once()
    mock_km.shutdown_kernel.assert_called_once_with(now=True)


@patch("jupyter_client.KernelManager")
def test_kernel_validator_execute_cell_success(mock_km_class):
    mock_kc = MagicMock()
    mock_kc.execute.return_value = "msg_123"

    # Simulate get_iopub_msg stream messages
    msg_stream = {
        "msg_type": "stream",
        "parent_header": {"msg_id": "msg_123"},
        "content": {"name": "stdout", "text": "hello stdout"}
    }
    msg_status = {
        "msg_type": "status",
        "parent_header": {"msg_id": "msg_123"},
        "content": {"execution_state": "idle"}
    }
    
    mock_kc.get_iopub_msg.side_effect = [msg_stream, msg_status]

    validator = SysMLKernelValidator()
    validator.kc = mock_kc

    res = validator.execute_cell("some code")
    assert res["status"] == "ok"
    assert res["stdout"] == ["hello stdout"]
    assert res["errors"] == []


@patch("jupyter_client.KernelManager")
def test_kernel_validator_execute_cell_error(mock_km_class):
    mock_kc = MagicMock()
    mock_kc.execute.return_value = "msg_123"

    msg_err = {
        "msg_type": "error",
        "parent_header": {"msg_id": "msg_123"},
        "content": {
            "ename": "SyntaxError",
            "evalue": "mismatched input 'party'",
            "traceback": ["line 1: typo here"]
        }
    }
    msg_status = {
        "msg_type": "status",
        "parent_header": {"msg_id": "msg_123"},
        "content": {"execution_state": "idle"}
    }

    mock_kc.get_iopub_msg.side_effect = [msg_err, msg_status]

    validator = SysMLKernelValidator()
    validator.kc = mock_kc

    res = validator.execute_cell("party SaturnV;")
    assert res["status"] == "error"
    assert "SyntaxError: mismatched input 'party'" in res["errors"]
    assert "line 1: typo here" in res["errors"]


@patch.object(SysMLKernelValidator, "execute_cell")
def test_kernel_validator_validate_file_fallback_publish(mock_execute_cell, tmp_path):
    # Simulate raw execution fails (e.g. because package element registration fails),
    # but the fallback %publish succeeded (syntax is okay).
    raw_error_response = {
        "status": "error",
        "errors": ["Compilation error: duplicated definition"],
        "warnings": [],
        "stdout": [],
        "display_data": [],
        "execute_result": []
    }
    publish_success_response = {
        "status": "ok",
        "errors": [],
        "warnings": [],
        "stdout": [],
        "display_data": [],
        "execute_result": []
    }
    show_success_response = {
        "status": "ok",
        "errors": [],
        "warnings": [],
        "stdout": ["package definition details"],
        "display_data": [],
        "execute_result": [{"text/plain": "package PkgA"}]
    }

    mock_execute_cell.side_effect = [
        raw_error_response,      # raw execute
        publish_success_response, # %publish fallback
        show_success_response    # %show check
    ]

    file_path = tmp_path / "PkgA.sysml"
    file_path.write_text("package PkgA {}", encoding="utf-8")

    validator = SysMLKernelValidator()
    result = validator.validate_file("PkgA", str(file_path))

    assert result.status == "pass"
    assert result.load_method == "publish"
    assert "Loaded via %publish" in result.warnings[0]
    assert len(result.errors) == 0


@patch.object(SysMLKernelValidator, "execute_cell")
def test_kernel_validator_run_viz_svg(mock_execute_cell, tmp_path):
    viz_payload = {
        "status": "ok",
        "errors": [],
        "warnings": [],
        "stdout": [],
        "display_data": [{"image/svg+xml": "<svg>diagram</svg>"}],
        "execute_result": []
    }
    mock_execute_cell.return_value = viz_payload

    validator = SysMLKernelValidator()
    res = validator.run_viz("PkgA", str(tmp_path), "tree")

    assert res.status == "pass"
    assert res.svg_path is not None
    assert os.path.exists(res.svg_path)
    with open(res.svg_path, "r") as f:
        assert f.read() == "<svg>diagram</svg>"


@patch.object(SysMLKernelValidator, "execute_cell")
def test_kernel_validator_run_viz_binary(mock_execute_cell, tmp_path):
    import base64
    dummy_pdf_b64 = base64.b64encode(b"PDF-1.4 header").decode("ascii")
    
    viz_payload = {
        "status": "ok",
        "errors": [],
        "warnings": [],
        "stdout": [],
        "display_data": [{"application/pdf": dummy_pdf_b64}],
        "execute_result": []
    }
    mock_execute_cell.return_value = viz_payload

    validator = SysMLKernelValidator()
    res = validator.run_viz("PkgA", str(tmp_path), "tree")

    assert res.status == "pass"
    assert res.pdf_path is not None
    assert os.path.exists(res.pdf_path)
    with open(res.pdf_path, "rb") as f:
        assert f.read() == b"PDF-1.4 header"


# ===========================================================================
# 3. NotebookGenerator Tests
# ===========================================================================

def test_notebook_generator_generate(tmp_path):
    report = ValidationReport(
        timestamp="2026-06-26T12:00:00Z",
        repo_path=str(tmp_path),
        total_files=1,
        passed=1,
        failed=0,
        total_time_s=1.5
    )
    
    file_path = tmp_path / "PkgA.sysml"
    file_path.write_text("package PkgA {}", encoding="utf-8")
    
    file_res = FileResult(
        package_name="PkgA",
        file_path=str(file_path),
        status="pass",
        load_method="raw",
        stdout_output=["OK stdout"]
    )
    report.file_results.append(file_res)

    viz_res = VizResult(
        element_name="PkgA",
        view_type="tree",
        status="pass",
        svg_path=str(tmp_path / "viz_PkgA_tree.svg")
    )
    # create the dummy svg file so the generator can read it
    with open(viz_res.svg_path, "w") as f:
        f.write("<svg></svg>")
    report.viz_results.append(viz_res)

    out_notebook = tmp_path / "test_out.ipynb"
    
    generator = NotebookGenerator()
    generator.generate(report, str(out_notebook))

    assert os.path.exists(out_notebook)
    with open(out_notebook, "r", encoding="utf-8") as f:
        nb_data = json.load(f)
    
    # Verify Notebook Structure
    assert nb_data["metadata"]["kernelspec"]["name"] == "sysml"
    assert len(nb_data["cells"]) > 0
    
    # We should have markdown cells and code cells
    cell_types = [c["cell_type"] for c in nb_data["cells"]]
    assert "markdown" in cell_types
    assert "code" in cell_types


# ===========================================================================
# 4. Orchestrator and CLI Tests
# ===========================================================================

def test_find_defining_package(tmp_path):
    # Setup Resolver with packages
    resolver = SysMLDependencyResolver(str(tmp_path))
    resolver.package_index = {
        "PkgA": "PkgA.sysml",
        "PkgB": "PkgB.sysml"
    }

    # Write contents for PkgB defining PkgBElement
    (tmp_path / "PkgA.sysml").write_text("package PkgA {}", encoding="utf-8")
    (tmp_path / "PkgB.sysml").write_text(
        "package PkgB {\n"
        "    part def PkgBElement;\n"
        "}",
        encoding="utf-8"
    )

    # 1. Match package name directly
    assert find_defining_package("PkgA", resolver) == "PkgA"

    # 2. Match element defined inside a package file
    assert find_defining_package("PkgBElement", resolver) == "PkgB"

    # 3. No match
    assert find_defining_package("NonExistent", resolver) is None


def test_run_validation_dry_run(tmp_path):
    # Create basic directory structure
    meta_content = {
        "index": {
            "PkgA": "PkgA.sysml",
            "PkgB": "PkgB.sysml"
        }
    }
    (tmp_path / ".meta.json").write_text(json.dumps(meta_content), encoding="utf-8")
    (tmp_path / "PkgA.sysml").write_text("package PkgA {}", encoding="utf-8")
    (tmp_path / "PkgB.sysml").write_text("package PkgB { import PkgA::*; }", encoding="utf-8")

    out_dir = tmp_path / "output"
    
    report = run_validation(
        repo_path=str(tmp_path),
        output_dir=str(out_dir),
        viz_elements=[("PkgA", "tree")],
        timeout=10,
        dry_run=True,
        continue_on_error=True
    )

    # In dry-run mode, it should successfully parse dependencies and return report without launching kernel
    assert report.total_files == 2
    assert report.loading_order == ["PkgA", "PkgB"]
    assert len(report.file_results) == 0  # No files validated in dry-run
    assert not os.path.exists(out_dir / "validation_report.json") # CLI generates file, run_validation function returns report object


def test_cli_args_parsing():
    test_args = [
        "validate_model.py",
        "--repo-path", "/dummy/path",
        "--output-dir", "/dummy/out",
        "--viz-elements", "SaturnV:tree,ApolloMission",
        "--timeout", "45",
        "--dry-run",
        "--no-continue-on-error"
    ]
    with patch.object(sys, "argv", test_args):
        # We patch run_validation so we only test CLI parsing
        with patch("validate_model.run_validation") as mock_run_val:
            mock_run_val.return_value = ValidationReport(passed=1, total_files=1)
            try:
                validate_model.main()
            except SystemExit:
                pass
            
            mock_run_val.assert_called_once_with(
                repo_path="/dummy/path",
                output_dir="/dummy/out",
                viz_elements=[("SaturnV", "tree"), ("ApolloMission", "tree")],
                timeout=45,
                dry_run=True,
                continue_on_error=False,
                target_package=None
            )


def test_cli_args_parsing_target_package():
    test_args = [
        "validate_model.py",
        "--repo-path", "/dummy/path",
        "--output-dir", "/dummy/out",
        "--viz-elements", "SaturnV:tree,ApolloMission",
        "--timeout", "45",
        "--dry-run",
        "--no-continue-on-error",
        "--target-package", "AirplanePackage"
    ]
    with patch.object(sys, "argv", test_args):
        with patch("validate_model.run_validation") as mock_run_val:
            mock_run_val.return_value = ValidationReport(passed=1, total_files=1)
            try:
                validate_model.main()
            except SystemExit:
                pass
            
            mock_run_val.assert_called_once_with(
                repo_path="/dummy/path",
                output_dir="/dummy/out",
                viz_elements=[("SaturnV", "tree"), ("ApolloMission", "tree")],
                timeout=45,
                dry_run=True,
                continue_on_error=False,
                target_package="AirplanePackage"
            )


# ===========================================================================
# 5. Validation Tests (Using Real SysML Kernel)
# ===========================================================================

@pytest.mark.skipif(not HAS_SYSML_KERNEL, reason="SysML Jupyter kernel not registered/available")
class TestRealSysMLKernelValidation:
    """
    Tests that run actual validation queries through the SysML Jupyter kernel.
    Specifically tests how the validator handles valid SysML, keyword/syntax errors,
    and dependency cascade failure skipping.
    """

    @pytest.fixture(autouse=True)
    def setup_validator(self):
        self.validator = SysMLKernelValidator(timeout=30)
        self.validator.start_kernel()
        yield
        self.validator.shutdown_kernel()

    def test_validate_valid_sysml(self, tmp_path):
        # Write valid SysML package
        file_path = tmp_path / "ValidPkg.sysml"
        file_path.write_text(
            "package ValidPkg {\n"
            "    part def ApolloSpacecraft;\n"
            "    part commandModule : ApolloSpacecraft;\n"
            "}",
            encoding="utf-8"
        )

        result = self.validator.validate_file("ValidPkg", str(file_path))
        assert result.status == "pass"
        assert len(result.errors) == 0
        assert result.load_method == "raw"


    def test_validate_invalid_sysml_syntax(self, tmp_path):
        # Write invalid SysML package with keyword typo (party instead of part)
        file_path = tmp_path / "InvalidSyntaxPkg.sysml"
        file_path.write_text(
            "package InvalidSyntaxPkg {\n"
            "    party SaturnV;\n"  # 'party' is a syntax error / keyword typo
            "}",
            encoding="utf-8"
        )

        result = self.validator.validate_file("InvalidSyntaxPkg", str(file_path))
        
        # Verify it registers as a failure
        assert result.status == "fail"
        assert len(result.errors) > 0
        # The error output from the kernel should highlight the syntax issue
        err_msg = "".join(result.errors)
        assert any(x in err_msg for x in ["party", "MismatchedTokenException", "SyntaxError", "Compilation", "no viable alternative"])


    def test_validate_invalid_dependency_cascade(self, tmp_path):
        # Package A has a syntax error
        pkg_a_file = tmp_path / "PkgA.sysml"
        pkg_a_file.write_text(
            "package PkgA {\n"
            "    party somePart; // Typo here\n"
            "}",
            encoding="utf-8"
        )

        # Package B imports A, and is valid itself
        pkg_b_file = tmp_path / "PkgB.sysml"
        pkg_b_file.write_text(
            "package PkgB {\n"
            "    import PkgA::*;\n"
            "    part b;\n"
            "}",
            encoding="utf-8"
        )

        # Write metadata index
        meta_content = {
            "index": {
                "PkgA": "PkgA.sysml",
                "PkgB": "PkgB.sysml"
            }
        }
        (tmp_path / ".meta.json").write_text(json.dumps(meta_content), encoding="utf-8")

        # Run orchestrator on this repo
        out_dir = tmp_path / "output"
        
        report = run_validation(
            repo_path=str(tmp_path),
            output_dir=str(out_dir),
            viz_elements=[],
            timeout=30,
            dry_run=False,
            continue_on_error=True
        )

        # Verify results: PkgA failed, PkgB skipped (dependency failure cascade prevented)
        file_results_dict = {res.package_name: res for res in report.file_results}
        
        assert "PkgA" in file_results_dict
        assert file_results_dict["PkgA"].status == "fail"
        
        assert "PkgB" in file_results_dict
        assert file_results_dict["PkgB"].status == "skipped"
        assert "dependency failed (PkgA)" in file_results_dict["PkgB"].errors[0]
        
        assert report.passed == 0
        assert report.failed == 1
        assert report.skipped == 1
