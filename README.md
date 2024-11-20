Key Features

YouTube API Integration:
  Fetch trending videos from YouTube based on country.
  Retrieve key metrics like views, likes, comments, and publication dates.
  
Data Management:
  Store retrieved video data in a local SQLite database.
  View, refresh, and manage data in an interactive table.
  Export data to CSV for offline analysis.

Advanced Visualization:
  Generate visual insights with Bar charts, Pie charts, Line graphs.
  Tree View window also offers visual inspection of database entries, and video playback.

Secure API Key Storage:
  Encrypt and securely store the API key locally using cryptography.
  Once saved, it will automatically load the decrypted key on application startup.

Customizable Options:
  Choose the country for scraping.
  Set the maximum number of results per scrape (1–50).
  Configure scheduled scraping intervals (e.g., every 10 minutes).

Automation with Scheduling:
  Automatically fetch data at user-defined intervals.
  Background thread ensures the application remains responsive during tasks.

Logging and Feedback:
  Built-in log system for real-time feedback on scraping and errors.