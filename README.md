# ShiftScan

Convert your shift schedule photo to an ICS calendar file in seconds.

**Demo:** [vardiya.egebostanci.me](https://vardiya.egebostanci.me)

[Türkçe](README_TR.md)

## Features

- OCR extraction from shift schedule images
- Manual text input support
- ICS calendar file generation
- Modern, responsive UI
- FastAPI backend

## Installation

1. Python 3.8+ required

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Create `.env` file for Gemini API:
```
GOOGLE_API_KEY=your_api_key_here
```

## Usage

```bash
python main.py
```

App runs at http://localhost:8000

## How It Works

1. Select the week's start date
2. Upload and crop your shift schedule image
3. Click "Scan" for OCR (or enter manually)
4. Click "Preview & Convert" to generate ICS
5. Download your calendar file

## Supported Formats

```
Mon 08:00 - 17:00
Tue OFF
Wed 14:00 - 22:00
```

### Day Abbreviations
- English: Mon, Tue, Wed, Thu, Fri, Sat, Sun
- Turkish: Pzt, Sal, Çar, Per, Cum, Cmt, Paz

### Day Off Keywords
OFF, LEAVE, REST, HOLIDAY

## License

MIT License
