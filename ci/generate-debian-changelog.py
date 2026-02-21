#!/usr/bin/env python3

# python3 md2debian.py Changelog.md > debian/changelog

import re
import sys
import os
from datetime import datetime
from email.utils import format_datetime
import textwrap

PACKAGE_NAME = "fping"
DEBIAN_DISTRIBUTION = "unstable"
DEBIAN_URGENCY = "low"
MAINTAINER_NAME = "David Schweikert"
MAINTAINER_EMAIL = "david@schweikert.ch"
MAX_LINE_LENGTH = 80

def validate_input_file(path):
  if not os.path.exists(path):
    sys.stderr.write(f"Error: File '{path}' does not exist.\n")
    sys.exit(1)
  
  if not os.path.isfile(path):
    sys.stderr.write(f"Error: '{path}' is not a regular file.\n")
    sys.exit(1)
  
  if not os.access(path, os.R_OK):
    sys.stderr.write(f"Error: File '{path}' is not readable.\n")
    sys.exit(1)

def parse_markdown_changelog(path):
  with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

  entries = []
  current = None
  current_section = None
  skip_next_block = False
  bullet_accumulator = None

  version_header_re = re.compile(r"^fping\s+([0-9.]+)\s+\((\d{4}-\d{2}-\d{2})\)")
  section_re = re.compile(r"^##\s+(.*)")
  bullet_re = re.compile(r"^\s*-\s+(.*)")
  continuation_re = re.compile(r"^\s{2,}(.*)")

  for line in lines:
    line = line.rstrip("\n")

    # Skip "Next" section
    if line.strip() == "Next":
      skip_next_block = True
      continue
    
    if skip_next_block:
      if version_header_re.match(line):
        skip_next_block = False
      else:
        continue
    
    m_version = version_header_re.match(line)
    if m_version:
      if current:
        if bullet_accumulator and current_section:
          current["sections"][current_section].append(bullet_accumulator.strip())
          bullet_accumulator = None
        entries.append(current)
      
      version = m_version.group(1)
      date_str = m_version.group(2)

      current = {
        "version": version,
        "date": date_str,
        "sections": {}
      }

      current_section = None
      continue

    if not current:
      continue
    
    m_section = section_re.match(line)
    if m_section:
      if bullet_accumulator and current_section:
        current["sections"][current_section].append(bullet_accumulator.strip())
        bullet_accumulator = None
      current_section = m_section.group(1).strip()
      current["sections"][current_section] = []
      continue
    
    m_bullet = bullet_re.match(line)
    if m_bullet and current_section:
      if bullet_accumulator:
        current["sections"][current_section].append(bullet_accumulator.strip())
      bullet_accumulator = m_bullet.group(1)
      continue
    
    m_cont = continuation_re.match(line)
    if m_cont and bullet_accumulator is not None:
      bullet_accumulator += " " + m_cont.group(1).strip()
      continue
    
    if bullet_accumulator and current_section and line.strip() == "":
      current["sections"][current_section].append(bullet_accumulator.strip())
      bullet_accumulator = None
  
  if current and bullet_accumulator and current_section:
    current["sections"][current_section].append(bullet_accumulator.strip())
    
  if current:
    entries.append(current)
  
  return entries

def format_debian_date(date_str):
  dt = datetime.strptime(date_str, "%Y-%m-%d")
  return format_datetime(dt)

def wrap_bullet(text, width=MAX_LINE_LENGTH):
  wrapper = textwrap.TextWrapper(width=width, initial_indent="    - ", subsequent_indent="      ")
  return wrapper.fill(text)

def generate_debian_changelog(entries):
  output = []

  for entry in entries:
    version = entry["version"]
    date = format_debian_date(entry["date"])

    header = f"{PACKAGE_NAME} ({version}) {DEBIAN_DISTRIBUTION}; urgency={DEBIAN_URGENCY}"
    output.append(header)
    output.append("")

    for section, items in entry["sections"].items():
      if not items:
        continue
      
      output.append(f"  * {section}")
      for item in items:
        output.append(wrap_bullet(item))
      output.append("")

    maint = f" -- {MAINTAINER_NAME} <{MAINTAINER_EMAIL}>  {date}"
    output.append(maint)
    output.append("")

  return "\n".join(output)

def main():
  if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} Changelog.md")
    sys.exit(1)

  md_path = sys.argv[1]
  validate_input_file(md_path)
  entries = parse_markdown_changelog(md_path)
  debian_changelog = generate_debian_changelog(entries)

  print(debian_changelog)

if __name__ == "__main__":
  main()