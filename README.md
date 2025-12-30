# anonflow

Automated bulk profile manipulation tool written in Python.

`anonflow` is a lightweight automation framework designed to perform bulk actions on browser profiles. The project is structured to be easily extensible, allowing users to define custom automation flows and actions.

## Features

- Bulk profile automation
- Modular action-based design
- Easy to extend with new automation scripts
- Python-based, simple setup
- Designed for browser automation workflows

## Project Structure

anonflow/
├── automate/ # Core automation logic
├── gpm/ # Profile / helper modules
├── actions.py # Action definitions
├── index.py # Main entry point
├── requirements.txt # Python dependencies
├── clean.bat # Cleanup script (Windows)
└── .gitignore

## Requirements

- Python 3.8+
- pip

## Installation

Clone the repository:

git clone https://github.com/thuongtruong109/anonflow.git
cd anonflow

Create a virtual environment (recommended):

python -m venv venv

Activate the environment:

Windows:
venv\Scripts\activate

Linux / macOS:
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

## Usage

Run the main script:

python index.py

Depending on your configuration, the script will execute predefined automation actions.

You can customize or add new actions in:

actions.py
automate/

## Customization

- Add new automation logic inside automate/
- Define reusable actions in actions.py
- Integrate with browser automation tools such as Selenium or Playwright
- Extend profile handling logic inside gpm/

## License

This project currently does not include a license file.
Add one (e.g. MIT, Apache 2.0) if you plan to distribute the project.

## Disclaimer

This project is intended for educational and testing purposes only.
Use responsibly and in compliance with applicable terms of service.
