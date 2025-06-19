# Verbiage generation scripts

## Project Structure

```
scripts/
├── data/                    # Data files
├── instructions/            # Game instructions and configurations
│   ├── en/                 # English language files
│   │   ├── character.md
│   │   ├── en_fivers.json
│   │   ├── things_to_avoid.md
│   │   └── word_response.md
│   └── fr/                 # French language files
│       └── fr_fivers.json
├── en_fivers.py            # extract the list of english words
├── en_game.py              # English word game
├── fr_fivers.py            # extract the list of french words
├── utils.py                # Utility functions
├── pyproject.toml          # Project configuration and dependencies
└── README.md               # This file
```

## Setup

### Prerequisites
- Python 3.8 or higher

### Installation

1. **Install the project in development mode:**
   ```bash
   pip install -e .
   ```

2. **Install development dependencies (including ruff formatter):**
   ```bash
   pip install -e .[dev]
   ```

   Or install both at once:
   ```bash
   pip install -e .[dev]
   ```

## Dependencies

### Core Dependencies
- **google-generativeai**: For AI-powered word generation and game logic
- **click**: For command-line interface functionality

### Development Dependencies
- **ruff**: Fast Python linter and formatter

## Code Formatting and Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for code formatting and linting.

### Running Ruff

**Check for linting issues:**
```bash
ruff check .
```

**Auto-fix issues where possible:**
```bash
ruff check . --fix
```

**Format code:**
```bash
ruff format .
```

**Check and format in one command:**
```bash
ruff check . --fix && ruff format .
```

### Ruff Configuration

The project is configured with:
- Line length: 88 characters (same as Black)
- Target Python version: 3.8+
- Enabled rules: pycodestyle (`E`) and Pyflakes (`F`)
- McCabe complexity checking (max complexity: 10)

## Scripts

### English Games
- `en_game.py`: General English word game

### French Games  
- `fr_fivers.py`: Five-letter word game in French

### Utilities
- `utils.py`: Shared utility functions

## Development Workflow

1. **Make your changes**
2. **Format and lint your code:**
   ```bash
   ruff check . --fix && ruff format .
   ```
3. **Test your changes**
4. **Commit your changes**

## Configuration Files

- `pyproject.toml`: Contains project metadata, dependencies, and tool configurations
- `instructions/`: Contains game-specific instructions and configurations in JSON and Markdown formats

## Batch Processing

For authentication:

```
brew install --cask google-cloud-sdk
gcloud auth application-default login
gcloud auth application-default set-quota-project gen-lang-client-0608167298
```