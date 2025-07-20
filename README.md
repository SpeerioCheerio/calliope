# Calliope - Advanced Vocabulary Enhancement App

A sophisticated vocabulary learning and enhancement application powered by OpenAI's GPT models. Calliope helps users build advanced vocabulary through AI-generated definitions, interactive flashcards, synonym discovery, and intelligent text analysis.

## Features

### Core Functionality
- **Word of the Day**: Daily vocabulary expansion with detailed word information
- **AI-Powered Word Addition**: Add words with automatically generated definitions, examples, and metadata
- **Smart Database**: Browse and filter your vocabulary collection with advanced search capabilities
- **Personal Thesaurus**: Find synonyms from your personal vocabulary database
- **Word Prediction**: AI-powered word suggestions for sentence completion
- **Interactive Flashcards**: Spaced repetition learning with customizable filters
- **Paragraph Analyzer**: Enhance your writing by identifying opportunities for vocabulary upgrades
- **Comprehensive Statistics**: Track your vocabulary growth and learning progress

### Advanced Features
- **Rarity Classification**: Words categorized by usage frequency (Common Advanced, Less Common, Rare/Archaic)
- **Sentiment Analysis**: Emotional tone classification for each word
- **Part-of-Speech Tagging**: Grammatical classification for better understanding
- **Example Sentences**: AI-generated contextual usage examples
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Powerful ORM for database operations
- **SQLite**: Lightweight, embedded database
- **OpenAI API**: GPT models for natural language processing
- **Pydantic**: Data validation and settings management
- **Python-dotenv**: Environment variable management

### Frontend
- **Vanilla JavaScript**: Modern ES6+ modules for clean, maintainable code
- **CSS3**: Advanced styling with gradients, animations, and responsive design
- **HTML5**: Semantic markup with accessibility features
- **Modular Architecture**: Component-based organization for scalability

### AI Integration
- **OpenAI GPT Models**: Primary model with automatic fallback
- **Custom Prompts**: Specialized prompts for vocabulary-specific tasks
- **Retry Logic**: Robust error handling with exponential backoff
- **Response Validation**: Ensures data quality and consistency

## Installation

### Prerequisites
- Python 3.8 or higher
- OpenAI API key
- Git (for cloning the repository)

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/calliope-app.git
   cd calliope-app
   ```

2. **Set Up Environment**
   ```bash
   cd backend
   cp env_template.txt .env
   # Edit .env and add your OpenAI API key
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the Application**
   ```bash
   python main.py
   ```

5. **Access the App**
   - Frontend: http://localhost:8000/static/index.html
   - API Documentation: http://localhost:8000/docs

### Alternative Startup
Use the automated startup script:
```bash
python start_app.py
```

## Configuration

### Environment Variables
Create a `.env` file in the `backend` directory with:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Database Configuration
DATABASE_URL=sqlite:///./calliope.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

### API Key Setup
1. Get your OpenAI API key from https://platform.openai.com/api-keys
2. Copy `env_template.txt` to `.env`
3. Replace the placeholder with your actual API key
4. Ensure your API key has sufficient credits and permissions

## Usage Guide

### Adding New Words
1. Navigate to "Add Word" section
2. Enter a word or phrase
3. AI generates definition, example, and metadata
4. Word is automatically saved to your database

### Studying with Flashcards
1. Go to "Flashcards" section
2. Filter by part of speech, rarity, or sentiment
3. Click cards to flip between word and definition
4. Use navigation controls to browse cards

### Finding Synonyms
1. Use the "Thesaurus" feature
2. Enter any word to find synonyms from your vocabulary
3. Discover connections between words you've learned

### Enhancing Writing
1. Use "Paragraph Analyzer"
2. Paste your text for analysis
3. Get suggestions for vocabulary upgrades
4. Replace simple words with more sophisticated alternatives

### Word Prediction
1. Go to "Word Prediction"
2. Enter a sentence with underscore (_) where you want suggestions
3. Get AI-powered word recommendations from your vocabulary

## Project Structure

```
calliope-app/
├── backend/                 # FastAPI backend
│   ├── main.py             # FastAPI application entry point
│   ├── models.py           # SQLAlchemy database models
│   ├── schemas.py          # Pydantic data validation schemas
│   ├── db.py               # Database configuration and utilities
│   ├── openai_client.py    # OpenAI API integration
│   ├── utils.py            # Utility functions
│   ├── requirements.txt    # Python dependencies
│   ├── env_template.txt    # Environment template
│   └── calliope.db         # SQLite database (created on first run)
├── frontend/               # Frontend application
│   ├── index.html          # Main HTML page
│   ├── style.css           # Styling and responsive design
│   ├── app.js              # Main application controller
│   ├── utils.js            # Shared utility functions
│   └── components/         # Modular JavaScript components
│       ├── addWord.js      # Word addition functionality
│       ├── viewDatabase.js # Database browser
│       ├── thesaurus.js    # Synonym finder
│       ├── prediction.js   # Word prediction
│       ├── flashcards.js   # Flashcard system
│       └── paragraphAnalyzer.js # Text analysis
├── start_app.py            # Automated startup script
├── starting_words.json     # Pre-populated vocabulary
├── words_enriched.json     # Enriched word data
└── README.md               # This file
```

## API Endpoints

### Core Endpoints
- `GET /api/word-of-the-day` - Get daily featured word
- `POST /api/add-word` - Add new word to database
- `GET /api/database` - Browse vocabulary with filters
- `POST /api/thesaurus` - Find synonyms
- `POST /api/predict` - Get word predictions
- `POST /api/analyze-paragraph` - Analyze text for enhancements
- `GET /api/flashcards` - Get flashcard data
- `GET /api/stats` - Get database statistics

### Utility Endpoints
- `GET /health` - Application health check
- `GET /api/parts-of-speech` - Available POS tags
- `GET /api/search` - Search vocabulary

## Database Schema

### Words Table
- `id`: Primary key
- `word`: Vocabulary word (unique)
- `pos`: Part of speech
- `definition`: AI-generated definition
- `example_sentence`: Usage example
- `rarity`: Frequency classification
- `sentiment`: Emotional tone
- `date_added`: Timestamp
- `last_reviewed`: Last study session

### Word of the Day Table
- `id`: Primary key
- `word_id`: Foreign key to words
- `date`: Date featured
- `created_at`: Timestamp

## Development

### Adding New Features
1. Backend: Add endpoints in `main.py`, models in `models.py`
2. Frontend: Create components in `components/` directory
3. Update routing in `app.js`
4. Add styling in `style.css`

### Database Migrations
The app uses SQLAlchemy with automatic table creation. For schema changes:
1. Update models in `models.py`
2. Delete `calliope.db` for fresh start (development only)
3. Or implement proper migrations for production

### Contributing
1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

## Troubleshooting

### Common Issues

**OpenAI API Errors**
- Verify API key is correct and has credits
- Check model availability (gpt-4o-mini vs gpt-3.5-turbo)
- Ensure proper .env file setup

**Database Issues**
- Delete `calliope.db` and restart to rebuild
- Check file permissions in backend directory
- Verify SQLite is properly installed

**Frontend Not Loading**
- Ensure backend is running on port 8000
- Check browser console for JavaScript errors
- Verify static file serving is working

**Installation Problems**
- Update pip: `pip install --upgrade pip`
- Try creating virtual environment: `python -m venv venv`
- Check Python version compatibility

### Performance Optimization
- Use database indexes for large vocabularies
- Implement caching for frequent API calls
- Consider upgrading to PostgreSQL for production
- Add CDN for static assets

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- OpenAI for providing powerful language models
- FastAPI community for excellent documentation
- SQLAlchemy team for robust ORM functionality
- All contributors and testers

**Start building your advanced vocabulary with Calliope today!** 