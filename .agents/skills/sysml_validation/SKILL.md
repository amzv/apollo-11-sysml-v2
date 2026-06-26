---
name: SysML Consistency Validation
description: Enforces that any created or modified SysML v2 code is validated using the local validate_model.py script to ensure correctness.
---

# SysML Code Validation Protocol

Whenever you are asked to generate, modify, or refactor SysML v2 (`.sysml`) code in this repository, you **MUST** follow this self-correction loop before presenting the final result to the user:

1. **Write/Modify Code**: Implement the requested SysML v2 code and save it to the appropriate `.sysml` file.
2. **Validate**: You must verify your code using the repository's validation script. Run the following command in the terminal:
   ```powershell
   python scripts/validate_model.py
   ```
   *(If you only want to validate a specific package or file and the script supports it, you may pass the appropriate arguments. Otherwise, run the full suite).*
3. **Analyze Output**: Carefully review the output of the validation script. Look for any errors reported by the SysML v2 Jupyter Kernel (e.g., syntax errors, reference errors, or failed `%show` / `%viz` commands).
4. **Iterate**: If the validation script reports errors or failures, you are NOT finished. You must read the error traceback, understand what went wrong with your SysML syntax, fix the code, and run the validation script again.
5. **Complete**: You may only consider the coding task complete and present it to the user once `validate_model.py` passes successfully for your changes.

**Why this is important**: SysML v2 has strict syntax and scoping rules. Relying on the deterministic feedback from `validate_model.py` allows you to catch and correct hallucinations or syntactical mistakes autonomously.
