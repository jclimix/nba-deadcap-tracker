import pandas as pd
from sql_utils.sql_transfers import extract_table_to_df
from loguru import logger
import os

def season_to_year(season: str) -> int:
    """Convert a season string (e.g., '2024-25') to the end year."""
    logger.debug("Converting season {} to year.", season)
    start_year, end_year_suffix = season.split('-')
    start_year = int(start_year)
    
    if end_year_suffix == "00":
        year = start_year + 1
    elif int(end_year_suffix) < int(str(start_year)[-2:]):
        year = int(str(start_year)[:2] + end_year_suffix)
    else:
        year = start_year + 1
    
    logger.debug("Season {} converted to year {}.", season, year)
    return year

def get_team_abbreviation(team_name, year):
    """Get the team abbreviation from the appropriate team mappings CSV based on the year."""
    logger.debug("Getting team abbreviation for team: {} and year: {}", team_name, year)

    if year == 2005:
        csv_file = '2005_team_mappings.csv'
    elif 2006 <= year <= 2008:
        csv_file = '2006-2008_team_mappings.csv'
    elif 2009 <= year <= 2012:
        csv_file = '2009-2012_team_mappings.csv'
    elif year == 2013:
        csv_file = '2013_team_mappings.csv'
    else:
        csv_file = 'modern_team_mappings.csv'

    csv_path = os.path.join('mappings', csv_file)
    logger.debug("Using CSV file: {}", csv_path)

    df = pd.read_csv(csv_path)
    row = df[df['team_name'] == team_name]
    abbreviation = row['team_abbreviation'].values[0] if not row.empty else "Team not found"

    logger.debug("Team abbreviation for {}: {}", team_name, abbreviation)
    return abbreviation

def filter_teams_by_abbreviation(data_df, team_abbreviation):
    """Filter the dataframe to include only players from the specified team."""
    logger.debug("Filtering players by team abbreviation: {}", team_abbreviation)
    valid_indices = []
    
    # find duplicate player ids
    duplicate_player_ids = data_df['player_id'].value_counts()
    multiple_appearances = duplicate_player_ids[duplicate_player_ids > 1].index

    for player_id in data_df['player_id'].unique():
        player_rows = data_df[data_df['player_id'] == player_id]
        
        if not player_rows.empty:
            if len(player_rows) > 1:
                # for players with multiple teams include only if last team matches
                last_row = player_rows.iloc[-1]
                if last_row['team'] == team_abbreviation:
                    valid_indices.append(last_row.name)
            else:
                # for players with one team, include if team matches
                first_row = player_rows.iloc[0]
                if first_row['team'] == team_abbreviation:
                    valid_indices.append(first_row.name)

    # filter the df and mark traded players
    result_df = data_df.loc[valid_indices].copy()
    result_df['player_name'] = result_df.apply(
        lambda row: f"{row['player_name']}*" if row['player_id'] in multiple_appearances else row['player_name'],
        axis=1
    )
    logger.debug("Filtered DataFrame shape after team abbreviation filter: {}", result_df.shape)
    return result_df

def add_salary_column(team_roster_df, salaries_df):
    """Add salary information to the team roster."""
    logger.debug("Adding salary column by merging roster and salary data.")
    merged_df = pd.merge(
        team_roster_df, 
        salaries_df[['player_id', 'salary']], 
        on='player_id', 
        how='left'
    )
    
    merged_df['salary'] = merged_df['salary'].fillna('$0')
    merged_df = merged_df.drop_duplicates(subset=['player_id'])
    merged_df = merged_df[['player_name', 'age', 'games_played', 'salary']]
    
    logger.debug("DataFrame shape after adding salary column: {}", merged_df.shape)
    return merged_df


def get_league_games_played(year):
    """Get the total number of games played in the league for a given year."""
    logger.debug("Getting league games played for year: {}", year)
    league_wins_teams_df = extract_table_to_df('league_wins_teams', 'salary')
    row = league_wins_teams_df[league_wins_teams_df['year'] == year]
    
    if not row.empty:
        total_wins = row['total_wins'].values[0]
        total_teams = row['total_teams'].values[0]
        total_games = (total_wins / total_teams) * 2
        logger.debug("League games played for year {}: {}", year, total_games)
        return total_games
    
    logger.warning("No league game data found for year: {}", year)
    return None

def get_salary_cap(season):
    """Get the salary cap for a given season."""
    logger.debug("Retrieving salary cap for season: {}", season)
    salary_caps_df = extract_table_to_df('salary_caps', 'salary')
    row = salary_caps_df[salary_caps_df['season'] == season]
    salary_cap = row['salary_cap'].values[0] if not row.empty else None
    logger.debug("Salary cap for season {}: {}", season, salary_cap)
    return salary_cap

def money_to_float(money_str):
    """Convert a money string to a float."""
    return float(money_str.replace('$', '').replace(',', ''))


def percent_to_float(percent_str):
    """Convert a percentage string to a float."""
    return float(percent_str.replace('%', '').strip())


def clean_salary_column(df):
    """Clean up salary column formatting."""
    logger.debug("Cleaning salary column formatting.")
    df['salary'] = df['salary'].replace('< $Minimum', '$0').str.extract(r'(\$[\d,]+)').fillna('$0')
    return df


def add_games_missed_column(df, total_games):
    """Add a column showing approximate games missed."""
    logger.debug("Adding games missed column with total games: {}", total_games)
    df['approx_games_missed'] = int(total_games) - df['games_played'].astype(int)
    return df


def add_dead_cap_column(df, total_games):
    """Calculate dead cap based on missed games."""
    logger.debug("Calculating dead cap using total games: {}", total_games)
    
    # Debug: Print DataFrame structure before processing
    logger.debug("DataFrame columns before processing: {}", df.columns.tolist())
    logger.debug("DataFrame dtypes before processing: \n{}", df.dtypes)
    
    # Debug: Print sample data for first few rows
    logger.debug("Sample data for first 2 rows:\n{}", df.head(2))
    
    # Debug: Test calculation on first row to check output type
    first_row = df.iloc[0]
    test_calc = (money_to_float(first_row['salary']) / (total_games - 1)) * first_row['approx_games_missed']
    logger.debug("Test calculation result type: {}, value: {}", type(test_calc), test_calc)
    
    try:
        # calculate one element at a time to isolate issues
        temp_results = []
        for _, row in df.iterrows():
            try:
                salary_float = money_to_float(row['salary'])
                games_missed = row['approx_games_missed']
                
                # handle potential type issues with games_missed
                if isinstance(games_missed, str) and '*' in games_missed:
                    games_missed = float(games_missed.replace('*', ''))
                else:
                    games_missed = float(games_missed)
                    
                calc_result = (salary_float / (total_games - 1)) * games_missed
                temp_results.append(calc_result)
                
                logger.debug("Row calculation - salary: {}, games_missed: {}, result: {}", 
                           salary_float, games_missed, calc_result)
            except Exception as e:
                logger.error("Error processing row {}: {}", row, str(e))
                temp_results.append(0)
        
        df['dead_cap_temp'] = temp_results
        logger.debug("Successfully created temporary column")
        
        # format the values
        df['dead_cap'] = df['dead_cap_temp'].apply(
            lambda x: f"- ${x:,.2f}" if x != 0 else "$0.00"
        )
        
        # drop temporary column
        df = df.drop(columns=['dead_cap_temp'])
        
    except Exception as e:
        logger.error("Error in dead cap calculation: {}", str(e))
        logger.error("Exception type: {}", type(e).__name__)
        # add placeholder column to prevent downstream errors
        df['dead_cap'] = "$0.00"
    
    # Debug: Check the final state
    logger.debug("DataFrame columns after processing: {}", df.columns.tolist())
    
    return df

def add_salary_per_game_column(df, total_games):
    """Calculate salary per game played."""
    logger.debug("Calculating salary per game using total games: {}", total_games)
    df['salary_per_game'] = df.apply(
        lambda row: (money_to_float(row['salary']) / total_games), 
        axis=1
    )
    
    df['salary_per_game'] = df['salary_per_game'].apply(lambda x: f"${x:,.2f}")
    
    return df


def add_pct_of_cap_column(df, season):
    """Calculate what percentage of the salary cap each player represents."""
    logger.debug("Calculating % of cap for season: {}", season)
    salary_cap = get_salary_cap(season)
    df['pct_of_cap'] = df.apply(
        lambda row: ((money_to_float(row['salary']) / money_to_float(salary_cap))) * 100, 
        axis=1
    )
    
    # format as percentage
    df['pct_of_cap'] = df['pct_of_cap'].apply(lambda x: f"{x:,.2f}%")
    
    return df


def sum_top_3_salaries(df):
    """Sum the top 3 salaries on the team."""
    logger.debug("Summing top 3 highest salaries.")
    top_3_salaries = df['salary'].apply(money_to_float).nlargest(3)
    total_top_3 = top_3_salaries.sum()
    total_top_3_str = f"${total_top_3:,.2f}"
    logger.debug("Total of top 3 salaries: {}", total_top_3_str)
    return total_top_3_str


def update_traded_players(df):
    """Update columns for players who were traded during the season."""
    logger.debug("Updating traded players with '*' markers.")
    # make columns are object type for string assignment
    df['approx_games_missed'] = df['approx_games_missed'].astype('object')
    df['dead_cap'] = df['dead_cap'].astype('object')
    
    # mark traded players with asterisk
    df.loc[df['player_name'].str.contains(r'\*', na=False), ['approx_games_missed', 'dead_cap']] = ['0*', '$0.00*']
    
    return df


def rename_columns(df):
    """Rename columns to more user-friendly names."""
    logger.debug("Renaming columns for final output.")
    return df.rename(columns={
        'player_name': 'Player',
        'age': 'Age',
        'games_played': 'Games Played',
        'salary': 'Salary',
        'approx_games_missed': 'Est. Games Not Played',
        'dead_cap': 'Dead Cap',
        'salary_per_game': 'Salary per Game',
        'pct_of_cap': '% of Cap'
    })

def sort_by_salary_desc(df):
    """Sort the dataframe by salary in descending order."""
    logger.debug("Sorting DataFrame by salary in descending order.")
    df['salary_float'] = df['salary'].apply(money_to_float)
    df = df.sort_values(by='salary_float', ascending=False).drop(columns=['salary_float'])
    return df

def get_team_data(season, team_name):
    """
    Process and return team salary data.
    This function is the main entry point when called from the Flask app.
    """
    logger.info("Processing team data for {} season and team {}.", season, team_name)
    
    # get team info
    year = season_to_year(season)
    team_abbr = get_team_abbreviation(team_name, year)
    
    # extract data from DB
    season_stats_df = extract_table_to_df(f'{year}_reg_season_stats', 'per_game_stats')
    team_roster_df = filter_teams_by_abbreviation(season_stats_df, team_abbr)
    salary_data_df = extract_table_to_df(f'{year}_player_salaries', 'salary')
    
    # processing all data
    df = add_salary_column(team_roster_df, salary_data_df)
    total_games = get_league_games_played(year)
    df = add_games_missed_column(df, total_games)
    df = clean_salary_column(df)
    df = add_dead_cap_column(df, total_games)
    df = add_salary_per_game_column(df, total_games)
    df = add_pct_of_cap_column(df, season)
    df = update_traded_players(df)
    
    # sort for final display
    df = sort_by_salary_desc(df)
    
    # get salary cap related stats
    salary_cap = get_salary_cap(season)
    total_salary = df['salary'].apply(money_to_float).sum()
    total_salary_str = f"${total_salary:,.2f}"
    
    amount_over_cap = float(total_salary) - money_to_float(salary_cap)
    amount_over_cap_str = f"${amount_over_cap:,.2f}"
    
    pct_of_cap_used = df['pct_of_cap'].apply(percent_to_float).sum()
    pct_of_cap_used_str = f"{pct_of_cap_used:,.2f}%"
    
    total_top_3_str = sum_top_3_salaries(df)
    
    top_3_cap_pct = (money_to_float(total_top_3_str) / money_to_float(salary_cap)) * 100
    top_3_cap_pct_str = f"{top_3_cap_pct:,.2f}%"
    
    team_logo_url = f"https://cdn.ssref.net/req/202502211/tlogo/bbr/{team_abbr}-{year}.png"
    
    df = rename_columns(df)
    
    # create summary dictionary
    summary = {
        'team_name': team_name,
        'season': season,
        'year': year,
        'team_abbr': team_abbr,
        'salary_cap': salary_cap,
        'total_salary': total_salary_str,
        'amount_over_cap': amount_over_cap_str,
        'pct_of_cap_used': pct_of_cap_used_str,
        'total_top_3': total_top_3_str,
        'top_3_cap_pct': top_3_cap_pct_str,
        'team_logo_url': team_logo_url,
        'total_games': round(total_games)
    }
    
    # return both roster df and the summary dict
    return df, summary

if __name__ == "__main__":

    df, summary = get_team_data("2005-06", "New Orleans Hornets")
    print(df)
    print("\nSummary:")
    for key, value in summary.items():
        print(f"{key}: {value}")