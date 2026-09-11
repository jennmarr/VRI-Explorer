# Exports every module-level dict literal in VRI_Explorer.py, plus every hardcoded
# "code - label" values tuple (e.g. data_src_vri_live_stem_ha_cd), to its own spreadsheet.
# One row per dict: the variable/field name in one cell, the dict itself in the other.
# Does not try to match dicts to fields in vri_fields.csv.

from pathlib import Path
import csv
import importlib.util
import json
import re

SCRIPT_DIR = Path(__file__).parent
SOURCE_MODULE = SCRIPT_DIR / "VRI_Explorer.py"
OUTPUT_CSV = SCRIPT_DIR.parent / "vri_dicts.csv"

# if is_field("X")[ or is_field("Y")...]:\n\t+values = ("code - label", ...)
INLINE_BLOCK = re.compile(r'if\s+((?:is_field\("[^"]+"\)(?:\s+or\s+)?)+):\n\t+values = \((.*?)\n\t+\)', re.S)
# if is_field("X")[ or is_field("Y")...]:\n\t+values = SOME_CONSTANT
REF_BLOCK = re.compile(r'if\s+((?:is_field\("[^"]+"\)(?:\s+or\s+)?)+):\n\t+values = ([A-Z][A-Z0-9_]*)\n')


def load_module():
	spec = importlib.util.spec_from_file_location("vri_explorer_source", SOURCE_MODULE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def strings_to_dict(tuple_body):
	value_dict = {}
	for entry in re.findall(r'"([^"]*)"', tuple_body):
		code, sep, label = entry.partition(" - ")
		value_dict[code.strip()] = label.strip() if sep else entry.strip()
	return value_dict


def parse_static_value_blocks(source_text):
	entries = []
	for if_clause, tuple_body in INLINE_BLOCK.findall(source_text):
		value_dict = strings_to_dict(tuple_body)
		for name in re.findall(r'is_field\("([^"]+)"\)', if_clause):
			entries.append((name, value_dict))
	for if_clause, const_name in REF_BLOCK.findall(source_text):
		const_match = re.search(rf'{const_name} = \((.*?)\n\)', source_text, re.S)
		if not const_match:
			continue
		value_dict = strings_to_dict(const_match.group(1))
		for name in re.findall(r'is_field\("([^"]+)"\)', if_clause):
			entries.append((name, value_dict))
	return entries


def main():
	module = load_module()
	rows = [
		{"name": name, "dict": json.dumps(value, ensure_ascii=False)}
		for name, value in vars(module).items()
		if isinstance(value, dict) and not name.startswith("_")
	]
	source_text = SOURCE_MODULE.read_text(encoding="utf-8")
	rows.extend(
		{"name": name, "dict": json.dumps(value_dict, ensure_ascii=False)}
		for name, value_dict in parse_static_value_blocks(source_text)
	)
	with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
		writer = csv.DictWriter(handle, fieldnames=("name", "dict"))
		writer.writeheader()
		writer.writerows(rows)
	print(f"Wrote {OUTPUT_CSV} ({len(rows)} dicts).")


if __name__ == "__main__":
	main()
