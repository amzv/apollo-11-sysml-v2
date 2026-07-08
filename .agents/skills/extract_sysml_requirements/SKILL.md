---
name: extract_sysml_requirements
description: Reads a standard from a PDF document, extracts physical requirements, generates a SysML v2 package, and iteratively validates it using validate_model.py until it passes.
---

# Extract SysML Requirements Workflow

When the user asks you to extract requirements from a standard (like a PDF) into SysML v2, you must follow this exact workflow:

## Step 1: Read the Source Standard
1. Use the `view_file` tool to read the PDF file provided by the user. 
2. Analyze the text to identify quantitative constraints, physical parameters, and explicit "shall" statements related to the system (e.g., vehicle dynamics, steady-state circular driving behavior).

## Step 2: Generate Initial SysML v2 Code
1. Draft the extracted requirements into SysML v2 syntax. 
2. Ensure you create a root `package` named after the standard (e.g., `package ISO4138_Requirements { ... }`).
3. Use proper SysML v2 constructs: `requirement def`, `requirement`, `doc` for descriptions, and `constraint` blocks if mathematical conditions are present.
4. Save this draft to a new file in the `REGULATORY_REQUIREMENTS/` directory (e.g., `REGULATORY_REQUIREMENTS/ISO4138_Requirements.sysml`) using the `write_to_file` tool. Ensure the path is absolute or relative to the workspace root.

## Step 3: Validation Loop
You must ensure the generated SysML v2 is perfectly valid according to the repository's rules.
1. Run the validation script on the file you just created using the `run_command` tool: 
   `python scripts/validate_model.py REGULATORY_REQUIREMENTS/<Your_File>.sysml`
2. **If the script passes:** The workflow is complete. Proceed to Step 4.
3. **If the script fails:** 
   - Analyze the syntax errors or semantic issues output by the script.
   - Use `replace_file_content` or `multi_replace_file_content` to fix the errors in the `.sysml` file.
   - Repeat Step 3 until the validation script returns a clean success. Do not ask the user for help unless you are stuck in an infinite loop.

## Step 4: Final Reporting
1. Once validation passes, present a summary to the user.
2. Show them the final verified requirements package.
3. Suggest the next step (e.g., creating a vehicle model that satisfies these requirements).
