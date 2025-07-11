# 📊 Trading Journal - Random's (Matt Mickey) Methodology

A comprehensive trading journal application built specifically for traders following Random's Four Steps methodology. This system helps traders track, analyze, and improve their trading performance using proven systematic approaches.

## 🎯 Features

### Core Trading Functionality
- **🎯 Trading Models**: Six pre-built models (0930 Open, HOD/LOD, P12, Captain Backtest, Quarterly, Midnight Open)
- **📈 Trade Tracking**: Complete trade lifecycle management with entry/exit points
- **💰 P&L Analytics**: Real-time profit/loss calculations and performance metrics
- **🏷️ Smart Tagging**: Color-coded tag system for trade categorization
- **📊 Performance Analytics**: Strike rates, profit factors, Kelly criterion, and more

### Random's Four Steps Integration
- **Step 1**: Define HOD/LOD using dashboard logic and time zones
- **Step 2**: Incorporate session variables (Asia, London, NY1, NY2)
- **Step 3**: Set realistic expectance using ADR and session analysis
- **Step 4**: Engage at highest statistical structure with price clouds

### Advanced Analytics
- **📈 Equity Curves**: Visual representation of trading performance
- **🎯 Risk Metrics**: Kelly fraction, maximum drawdown, MFE analysis
- **📅 Daily Journals**: Pre-market analysis, P12 scenarios, mental state tracking
- **🔍 Model Insights**: AI-powered recommendations based on Random's methodology

### P12 Scenario System
- **5 Core P12 Scenarios**: Complete scenario library with visual aids
- **📋 Trading Implications**: HOD/LOD predictions and directional bias
- **⚠️ Alert Criteria**: What to watch for in each scenario
- **✅ Confirmation Logic**: How to validate scenario selection

## 🚀 Quick Start

### Installation Steps

#### 1. Clone the Repository
```bash
git clone https://github.com/smitty1021/TDP_Trading_Journal
cd trading-journal
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
FLASK_ENV=development
FLASK_DEBUG=True
```

#### 5. Initialize Database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

#### 6. Create Default Data
```bash
python create_default_data.py
```

#### 7. Run the Application
```bash
python run.py
```

Visit `http://localhost:5000` in your browser!

## 📋 Default Login

- **Username**: `admin`
- **Password**: `admin123`

## 🐛 Troubleshooting

### Common Issues

#### Database Errors
```bash
# Reset database
flask db downgrade
flask db upgrade
```

#### Missing Dependencies
```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```
