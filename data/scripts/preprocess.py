import os
import re
import json

def preprocess_law(text, act_name="Unknown Act"):
    structured_data = {
        "Act": act_name,
        "Parts": {}
    }

    current_part = "General"
    current_section = None

    
    part_pattern = re.compile(r'Part\s+([IVXLC]+)\s*[-–]?\s*(.*)', re.IGNORECASE)
    section_pattern = re.compile(r'^\s*(\d+)\.\s*(.*)', re.MULTILINE)
    definition_pattern = re.compile(r'"([^"]+)"\s+means\s+(.*?)(?=(;|$))', re.IGNORECASE)

    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        
        part_match = part_pattern.match(line)
        if part_match:
            roman, heading = part_match.groups()
            current_part = f"Part {roman} – {heading.strip()}"
            structured_data["Parts"].setdefault(current_part, {})
            current_section = None
            continue

        
        section_match = section_pattern.match(line)
        if section_match:
            section_num, heading = section_match.groups()
            current_section = section_num
            structured_data["Parts"].setdefault(current_part, {})
            structured_data["Parts"][current_part][current_section] = {
                "Heading": heading.strip(),
                "Content": ""
            }
            continue

        
        if current_section:
            structured_data["Parts"][current_part][current_section]["Content"] += " " + line
        else:
           
            structured_data["Parts"].setdefault(current_part, {})
            structured_data["Parts"][current_part].setdefault("Preamble", {"Heading": "Preamble", "Content": ""})
            structured_data["Parts"][current_part]["Preamble"]["Content"] += " " + line

   
    for part, sections in structured_data["Parts"].items():
        for sec_num, sec_data in sections.items():
            if "interpretation" in sec_data["Heading"].lower():
                definitions = {}
                for match in definition_pattern.finditer(sec_data["Content"]):
                    term, meaning, _ = match.groups()
                    definitions[term.strip()] = meaning.strip()
                if definitions:
                    sec_data["Definitions"] = definitions

    return structured_data


if __name__ == "__main__":
    input_dir = "../Cleaned Acts"
    output_dir = "../ActsinJson"

    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            act_name = os.path.splitext(filename)[0]
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{act_name}.json")

            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()

            structured = preprocess_law(text, act_name=act_name)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(structured, f, indent=4, ensure_ascii=False)

            print(f" {filename} processed → {output_path}")
