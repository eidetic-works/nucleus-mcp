import re

with open("src/mcp_server_nucleus/tools/orchestration.py", "r") as f:
    content = f.read()

fix_code_impl = '''
    def _fix_code(file_path: str, issues_context: str) -> str:
        try:
            path = Path(file_path)
            if not path.exists():
                return json.dumps({"status": "error", "message": "File not found"})

            original_content = path.read_text(encoding='utf-8')
            
            # 1. Create Backup
            backup_path = path.with_suffix(f"{path.suffix}.bak")
            backup_path.write_text(original_content, encoding='utf-8')

            # 2. Invoke LLM (Fixer Persona)
            system_prompt = (
                "You are 'The Fixer', an autonomous code repair agent. "
                "Your goal is to fix specific issues in the provided code while maintaining strict adherence to the project's style (Nucleus/Neon/Context-Aware). "
                "Return ONLY the full corrected file content inside a code block. Do not wrap in markdown or add commentary."
            )
            
            user_prompt = f"""
            TARGET: {file_path}
            
            ISSUES TO FIX:
            {issues_context}
            
            CURRENT CONTENT:
            ```
            {original_content}
            ```
            
            INSTRUCTIONS:
            1. Fix the issues listed above.
            2. Ensure accessibility (ARIA) and style compliance (Globals/Neon) if UI.
            3. Do NOT break existing logic.
            4. Return the COMPLETE new file content.
            """

            from ..runtime.llm_client import DualEngineLLM
            
            llm = DualEngineLLM() 
            fix_response = llm.generate_content(
                prompt=user_prompt,
                system_instruction=system_prompt
            )

            # 3. Extract Code
            new_content = fix_response.text.strip()
            if "```" in new_content:
                parts = new_content.split("```")
                candidate = parts[1]
                if candidate.startswith(("typescript", "tsx", "python", "css", "javascript", "json")):
                     candidate = "\\n".join(candidate.split("\\n")[1:])
                new_content = candidate
            
            # 4. Write Fix
            path.write_text(new_content, encoding='utf-8')
            
            return json.dumps({
                "status": "success", 
                "message": f"Applied fix to {path.name}",
                "backup": str(backup_path)
            })

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    def brain_fix_code(file_path: str, issues_context: str) -> str:
        """Auto-fix code based on issues context."""
        return _fix_code(file_path, issues_context)
'''

# Find the old brain_fix_code and replace it
old_block = '''    @mcp.tool()
    def brain_fix_code(file_path: str, issues_context: str) -> str:
        """Auto-fix code based on issues context."""
        return helpers["brain_fix_code"](file_path, issues_context)'''

if old_block in content:
    content = content.replace(old_block, fix_code_impl.strip("\n"))
    with open("src/mcp_server_nucleus/tools/orchestration.py", "w") as f:
        f.write(content)
    print("Patch applied to orchestration.py.")
else:
    print("Old block not found!")
