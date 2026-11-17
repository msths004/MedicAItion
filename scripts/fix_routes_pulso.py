# -*- coding: utf-8 -*-
import py_compile
import re

for base in [r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion", r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"]:
    p = base + r"\app\api\routes_pulso.py"
    with open(p, "r", encoding="utf-8") as f:
        code = f.read()

    # Remove the bad line in ollama try block
    code = code.replace("                    await asyncio.sleep(0.003)\n", "")
    code = code.replace("await asyncio.sleep(0.003)\n", "")

    # Clean GGUF loop
    pattern = r'(for token in stream_local_llm_chat\(messages, temperature=0\.25\):.*?\n\s+yield \(json\.dumps\(\{"type": "token", "content": token\}, ensure_ascii=False\) \+ "\\n"\)\.encode\("utf-8"\))'
    
    match = re.search(pattern, code, flags=re.DOTALL)
    if match:
        replacement = match.group(1) + '\n                    await asyncio.sleep(0.003)'
        code = code[:match.start()] + replacement + code[match.end():]

    with open(p, "w", encoding="utf-8") as f:
        f.write(code)

    py_compile.compile(p, doraise=True)
    print(f"Successfully compiled {p} without syntax errors!")
