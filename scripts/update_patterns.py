import json
import os

# === File paths ===
problems_file = "database/problems_database.json"
patterns_file = "database/patterns.json"

# === Load problems database ===
with open(problems_file, "r", encoding="utf-8") as file:
    problems = json.load(file)

# === Create new patterns dictionary ===
patterns = {}

for code, details in problems.items():
    clean_code = code.split()[0].upper()

    keywords = []

    # Always include the error code itself
    keywords.append(clean_code.lower())

    # Extract words from 'problem' field
    description = details.get("problem", "").lower()

    for word in description.split():
        word = word.strip(",.()[]{}")
        if word.isalpha() and len(word) > 3:
            keywords.append(word)

    # Remove duplicates
    keywords = list(set(keywords))

    # Build Regex pattern like (word1|word2|word3)
    regex = "(" + "|".join(keywords) + ")"

    # Add to dictionary
    patterns[clean_code] = regex

# === Save patterns.json ===
with open(patterns_file, "w", encoding="utf-8") as file:
    json.dump(patterns, file, indent=4, ensure_ascii=False)

print(f"File {patterns_file} has been successfully updated with Regex patterns!")
