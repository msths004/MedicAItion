import os
import re

p = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\scripts\seed_demo_patients.py"
with open(p, "r", encoding="utf-8") as f:
    text = f.read()

# Extract all dictionaries in PATIENTS_DATA
matches = re.findall(r'\{\s*"nombres":\s*"([^"]+)",\s*"primer_apellido":\s*"([^"]+)",[\s\S]*?"curp":\s*"([^"]+)",[\s\S]*?"disease_name":\s*"([^"]+)",\s*"cie10_code":\s*"([^"]+)",\s*"specialty":\s*"([^"]+)"', text)
print(f"Total matched: {len(matches)}")
for idx, m in enumerate(matches):
    print(f"{idx+1}. {m[0]} {m[1]} | CURP: {m[2]} | {m[3]} ({m[4]}) - {m[5]}")
