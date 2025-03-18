from flask import Flask, render_template, request, jsonify
import pandas as pd
from loguru import logger
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import analyze_dead_cap as analyzer
from waitress import serve

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10 per minute"]
)

# Configure Loguru
logger.add("logs/nba_dead_cap_app.log", rotation="10 MB")

AVAILABLE_SEASONS = [
    "2004-05", "2005-06", "2006-07", "2007-08", "2008-09", "2009-10", 
    "2010-11", "2011-12", "2012-13", "2013-14", "2014-15",
    "2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"
]

def get_version():
    try:
        with open('version.txt', 'r') as f:
            version = f.read().strip()
        return version
    except Exception as e:
        print(f"Error reading version file: {e}")
        return "v?.?.?"

def get_teams_for_season(season):
    """
    Get the available teams for a specific season by loading the appropriate mapping CSV.
    """
    try:

        year = analyzer.season_to_year(season)
        logger.debug(f"Getting teams for year: {year}")
        
        # mapping CSV file based on the year
        if year == 2005:
            csv_file = '2005_team_mappings.csv'
        elif 2006 <= year <= 2008:
            csv_file = '2006-2008_team_mappings.csv'
        elif 2009 <= year <= 2012:
            csv_file = '2009-2012_team_mappings.csv'
        elif year == 2013:
            csv_file = '2013_team_mappings.csv'
        else:  # 2014 and later
            csv_file = 'modern_team_mappings.csv'
            
        csv_path = os.path.join('mappings', csv_file)
        logger.debug(f"Using CSV file: {csv_path}")
        
        df = pd.read_csv(csv_path)
        teams = df['team_name'].tolist()
        teams.sort()  
        
        logger.debug(f"Found {len(teams)} teams for season {season}")
        return teams
        
    except Exception as e:
        logger.error(f"Error loading teams for season {season}: {str(e)}")

        return ["Error loading teams, please try another season"]
    
version = get_version()

@app.route('/')
def index():
    """Render the main page with form to select season and team."""
    default_season = "2008-09"

    # get teams for the default season
    teams = get_teams_for_season(default_season)
    default_team = "Los Angeles Lakers" if "Los Angeles Lakers" in teams else teams[0]
    
    return render_template('index.html', 
                           seasons=AVAILABLE_SEASONS, 
                           teams=teams, 
                           default_season=default_season,
                           default_team=default_team,
                           version=version)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process form submission and show team data."""
    try:
        # get parameters from form
        season = request.form.get('season', "2008-09")
        team_name = request.form.get('team', "Los Angeles Lakers")
        
        logger.info(f"Analyzing {season} data for {team_name}")
        
        # analyzer func to get the data
        df, summary = analyzer.get_team_data(season, team_name)
        
        table_html = df.to_html(classes='table table-striped table-bordered', index=False)
        
        # get teams for the selected season for the dropdown
        teams = get_teams_for_season(season)
        
        return render_template('results.html', 
                               table=table_html, 
                               summary=summary,
                               seasons=AVAILABLE_SEASONS,
                               teams=teams,
                               version=version)
    
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/api/team-data', methods=['GET'])
def api_team_data():
    """API endpoint to get team data in JSON format."""
    try:

        season = request.args.get('season', "2005-06")
        team_name = request.args.get('team', "New Orleans Hornets")
        
        logger.info(f"API request for {season} data for {team_name}")
        

        df, summary = analyzer.get_team_data(season, team_name)
        
        roster_data = df.to_dict(orient='records')
        
        response = {
            'summary': summary,
            'roster': roster_data
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<season>', methods=['GET'])
def api_teams_for_season(season):
    """API endpoint to get list of teams for a specific season."""
    try:
        teams = get_teams_for_season(season)
        return jsonify({'teams': teams})
    except Exception as e:
        logger.error(f"API error when getting teams for {season}: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8009)