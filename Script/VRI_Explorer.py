# Spreadsheet Driven Version
# Date             : Sept 29 2026
#
# Author:          : Jennifer Marr (jennifer.marr@gov.bc.ca)
#
# Purpose:         : Visualize the VRI data and corresponding meaning of fields and values found within
#
# 				   : The script:
# 				     reads spreadsheet rows from vri_fields.csv
#  				     build field objects from name, alias, description, example, values
#  				     render HTML cards
#  				     write index.html
# 					 the field data is coming from the spreadsheet, except for a few non-data pieces:
#  				     styling in the HTML string
# 					 page title / headings / layout text
# 					 the browser search behavior
# the re.sub(...) cleanup applied to value text for display
#
# Inputs:          : vri_fields.csv
#
# History:         : (2026-09-09) Created from Dan's DBP06 explorer and the pdf found here: https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/stewardship/forest-analysis-inventory/data-management/standards/vegcomp_poly_rank1_data_dictionaryv5_2019.pdf
# 				   : (2026-09-10) Updated so was driven by .csv, manual corrections applied


from pathlib import Path
from html import escape
import ast
import csv
import re


OUTPUT = Path(r"\\bctsdata.bcgov\data\north_root\Library\Scripts\VRI_Explorer\index.html")
FIELDS_CSV = Path(r"\\bctsdata.bcgov\data\north_root\Library\Scripts\VRI_Explorer\Inputs\vri_fields.csv")

def read_fields_csv(path):
	with path.open("r", newline="", encoding="utf-8-sig") as handle:
		return list(csv.DictReader(handle))


def parse_values(value_text):
	value_text = value_text.strip()
	if value_text.startswith("{") and value_text.endswith("}"):
		try:
			parsed_value = ast.literal_eval(value_text)
		except (SyntaxError, ValueError):
			parsed_value = None
		if isinstance(parsed_value, dict):
			return parsed_value
		if isinstance(parsed_value, (list, tuple, set)):
			return tuple(str(value) for value in parsed_value)
	return tuple(part.strip().strip('"') for part in value_text.split("|") if part.strip())


def rows_to_fields(rows):
	# Builds cards directly from the (user-corrected) CSV; no PDF parsing or guesswork.
	fields = {}
	for row in rows:
		name = (row.get("name") or "").strip()
		if not name:
			continue
		alias = (row.get("alias") or "").strip()
		description = (row.get("description") or "").strip()
		example = (row.get("example") or "").strip()
		values = parse_values(row.get("values") or "")
		field = (name, alias, description, example, values)
		if name not in fields:
			fields[name] = field
		else:
			previous = fields[name]
			if isinstance(previous[4], tuple) and isinstance(field[4], tuple):
				combined_values = tuple(dict.fromkeys(previous[4] + field[4]))[:20]
			else:
				combined_values = previous[4]
			fields[name] = (previous[0], previous[1], previous[2], previous[3], combined_values)
	return list(fields.values())


def value_labels(value):
	if isinstance(value, dict):
		return [label for key, nested_value in value.items() for label in value_labels(nested_value) if key]
	return [str(value).strip().strip('"')]


def value_chip(key, value=""):
	key = str(key).strip().strip('"')
	value = str(value).strip().strip('"')
	tooltip_attributes = ""
	if value:
		tooltip_attributes = (
			f' data-tooltip="{escape(value)}" '
			f'onmouseenter="this.closest(\'.field\').querySelector(\'.card-tooltip\').textContent=this.dataset.tooltip" '
			f'onmouseleave="this.closest(\'.field\').querySelector(\'.card-tooltip\').textContent=\'\'"'
		)
	return (
		f'<span class="chip"{tooltip_attributes} style="display:inline-block;max-width:100%;box-sizing:border-box;'
		f'padding:6px 10px;border:1px solid #bfd7c2;border-radius:0;background:#dcebe0;'
		f'color:#315b49;font-weight:600;margin:4px 2px;white-space:normal;'
		f'overflow-wrap:anywhere;vertical-align:top;">{escape(key)}</span>'
	)


def nested_value_lines(values):
	lines = []
	for key, value in values.items():
		key = str(key).strip().strip('"')
		if isinstance(value, dict):
			lines.extend(nested_value_lines(value))
		else:
			lines.append(f"{key} - {str(value).strip().strip(chr(34))}")
	return lines


def value_html(values, show_value=False):
	if isinstance(values, dict):
		items = []
		for key, value in values.items():
			key = str(key).strip().strip('"')
			if isinstance(value, dict):
				hover_label = key
				subvalues = value
				if isinstance(value.get("name"), str) and isinstance(value.get("subcodes"), dict):
					hover_label = value["name"].split("(", 1)[0].strip().strip('"')
					subvalues = value["subcodes"]
				elif len(value) == 1:
					category, category_values = next(iter(value.items()))
					if isinstance(category_values, dict):
						hover_label = str(category).split("(", 1)[0].strip()
						subvalues = category_values
				subcode_lines = nested_value_lines(subvalues)
				if subcode_lines:
					lines = "<br>".join(escape(line) for line in subcode_lines)
					items.append(
						f'<details class="value-group"><summary class="chip" data-tooltip="{escape(hover_label)}" onmouseenter="this.closest(\'.field\').querySelector(\'.card-tooltip\').textContent=this.dataset.tooltip" '
						f'onmouseleave="this.closest(\'.field\').querySelector(\'.card-tooltip\').textContent=\'\'" style="display:inline-block;padding:6px 10px;'
						f'border:1px solid #bfd7c2;border-radius:0;background:#dcebe0;color:#315b49;'
						f'font-weight:600;margin:4px 2px;cursor:pointer;">{escape(key)}</summary>'
						f'<div class="nested-values">{lines}</div></details>'
					)
				else:
					items.append(value_chip(key, hover_label))
			else:
				items.append(value_chip(f"{key} - {value}") if show_value else value_chip(key, value))
		return "".join(items)
	return "".join(
		value_chip(value)
		for value in values
	)


def field_cards(fields):
	cards = []
	for name, alias, description, example, values in fields:
		labels = value_labels(values)
		value_block_html = f'<div class="value-list">{value_html(values)}</div>'
		example_html = f'<strong>e.g. {escape(example)}</strong>' if example else ""
		search_text = " ".join((name, alias, description, *labels))
		cards.append(
			f'<article class="field" data-search="{escape(search_text.lower())}">'
			f'<code>{escape(name)}</code>{example_html}'
			f'<p>{escape(description)}</p>{value_block_html}<div class="card-tooltip"></div></article>'
		)
	return "".join(cards)

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>.field code{max-width:100%;overflow-wrap:anywhere;word-break:break-word}.card-tooltip{max-width:100%;box-sizing:border-box;margin-top:8px;padding:8px 10px;border:1px solid #315b49;border-radius:0;background:#fffdf8;color:#17231f;font:12px/1.35 Segoe UI,system-ui,sans-serif;overflow-wrap:anywhere}.card-tooltip:empty{display:none}.value-group{display:inline-block;max-width:100%}.nested-values{max-width:100%;margin:4px 2px;padding:8px 10px;border:1px solid #bfd7c2;border-radius:0;background:#dcebe0;color:#315b49;font-size:12px;font-weight:600;line-height:1.5;overflow-wrap:anywhere}</style>
<title>VRI Field Explorer</title><style>
:root{--ink:#17231f;--muted:#68756e;--paper:#f6f3eb;--panel:#fffdf8;--line:#d9ddd3;--green:#315b49;--mint:#dcebe0;--gold:#c18b3c}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 90% 0,#dcebe0,transparent 30rem),var(--paper);color:var(--ink);font:15px/1.5 Segoe UI,system-ui,sans-serif}header{padding:36px 6vw 28px;border-bottom:1px solid var(--line)}.eyebrow{color:var(--gold);font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}.title{margin:8px 0 5px;font:700 clamp(34px,5vw,58px)/1 Georgia,serif}.lede{color:var(--muted);max-width:680px}.toolbar{padding:20px 6vw;position:sticky;top:0;background:#f6f3ebed;backdrop-filter:blur(10px);z-index:2;border-bottom:1px solid var(--line)}input{width:min(740px,100%);padding:13px 16px;border:1px solid var(--line);border-radius:7px;background:var(--panel);font:inherit}.layout{max-width:1400px;margin:auto;padding:30px 6vw 70px}.results{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:15px}.field{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px;min-height:220px}.field:hover{border-color:#9dbca7;box-shadow:0 15px 35px #20352b14}.field code{display:block;color:var(--green);font:bold 18px Consolas,monospace}.field strong{display:block;margin:8px 0}.field small{color:var(--gold);text-transform:uppercase;letter-spacing:.08em}.field p{color:var(--muted);font-size:13px;min-height:55px}.value-list{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}.value-chip{position:relative;display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--green);color:#fff;font:700 12px Consolas,monospace;cursor:help}.value-chip:hover{background:var(--gold)}.value-chip::after{content:attr(data-tooltip);position:absolute;left:50%;bottom:calc(100% + 9px);transform:translateX(-50%) translateY(4px);width:max-content;max-width:240px;padding:8px 10px;border-radius:5px;background:var(--ink);color:#fff;font:12px/1.35 Segoe UI,system-ui,sans-serif;pointer-events:none;opacity:0;transition:.15s;z-index:3}.value-chip:hover::after{opacity:1;transform:translateX(-50%) translateY(0)}.chip{display:inline-block;background:#f2f8f1;border:1px solid #bdd1c2;border-radius:4px;padding:3px 7px;margin:2px;color:var(--green);font:12px Consolas,monospace}.lookup-block{margin:8px 0}.lookup-block summary{cursor:pointer;color:var(--green);font-weight:600}.lookup-block table{border-collapse:collapse;background:#fff;border:1px solid var(--line);font-size:12px}.lookup-block td{padding:6px 8px;border:1px solid var(--line)}.field button{margin-top:14px;border:0;background:var(--mint);color:var(--green);padding:8px 10px;border-radius:5px}.empty{color:var(--muted);padding:50px;text-align:center}dialog{border:0;border-radius:9px;max-width:650px;padding:26px;background:var(--panel);color:var(--ink);box-shadow:0 20px 70px #17231f55}dialog::backdrop{background:#17231f66}dialog button{border:0;background:var(--mint);padding:8px 12px;color:var(--green);border-radius:5px}@media(max-width:700px){.layout{padding-top:18px}}
</style></head><body><header><div class="eyebrow">Vegetation Resources Inventory · Version 5.0</div><h1 class="title">VRI Field Explorer</h1><p class="lede">Explore fields, coded values, and the forestry meaning behind each attribute.</p></header><div class="toolbar"><input id="search" type="search" placeholder="Search fields, meanings, or codes..."></div><main class="layout"><div class="results" id="results">__CARDS__</div></main><dialog id="details"><div id="detail"></div><button onclick="details.close()">Close</button></dialog><script>const search=document.querySelector('#search'),cards=[...document.querySelectorAll('.field')];search.oninput=()=>{const q=search.value.toLowerCase();cards.forEach(card=>card.hidden=!card.dataset.search.includes(q))};function showField(button){detail.innerHTML='<h2>'+button.dataset.name+'</h2><h3>'+button.dataset.alias+'</h3><p>'+button.dataset.description+'</p><p><b>Example:</b> '+button.dataset.example+'</p><h4>Coded values and guidance</h4><p>'+button.dataset.values.split('|').join('<br>')+'</p>';details.showModal()}</script></body></html>"""


def main():
	if not FIELDS_CSV.exists():
		raise SystemExit(f"{FIELDS_CSV} not found. Export/create it before running.")
	fields = rows_to_fields(read_fields_csv(FIELDS_CSV))
	if not fields:
		raise SystemExit(f"No field entries were found in {FIELDS_CSV}.")
	page = HTML.replace("__CARDS__", field_cards(fields))
	OUTPUT.write_text(page, encoding="utf-8")
	print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
	main()
