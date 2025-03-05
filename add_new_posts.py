import pandas as pd
import json
import os
import praw
import logging
from datetime import datetime
from thefuzz import process
from openai import OpenAI
import re
from dotenv import load_dotenv
load_dotenv()

# Logging setup
logging.basicConfig(filename="perfume_scraper.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv("PRAW_CLIENT_ID"),
    client_secret=os.getenv("PRAW_CLIENT_SECRET"),
    user_agent=os.getenv("PRAW_USER_AGENT")
)

subreddit_name = "tester_jethya"
keyword = "wts"  # Change this to your desired keyword
subreddit = reddit.subreddit(subreddit_name)

CSV_FILE = "merged_perfume_data_copy.csv"
JSON_FILE = "montagne_official_data.json"

# Load JSON data
with open(JSON_FILE, "r", encoding="utf-8") as f:
    json_data = json.load(f)
json_df = pd.DataFrame(json_data)
json_df.rename(columns={"name": "Perfume_name", "url": "official_link", "is_in_stock": "official_availability", "price": "official_price"}, inplace=True)

# Load existing CSV
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
else:
    df = pd.DataFrame(columns=["post_id", "link_flair_text", "Perfume_name", "permalink", "bottle_cost", "clone_of", "official_link", "official_availability", "official_price"])

def parse_perfume_post(post_text: str) -> list:
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")
    system_prompt = """
    Extract perfume details from the following Reddit post and format them as a list of dictionaries:
    - Perfume_name
    - bottle_quantity (default to 50ml if not specified)
    - bottle_cost
    - currency (default to USD)

    Example output:
    [
        {"Perfume_name": "Guerlain Homme", "bottle_quantity": "100ml", "bottle_cost": 50, "currency": "USD"},
        {"Perfume_name": "Pacific Moss", "bottle_quantity": "50ml", "bottle_cost": 35, "currency": "USD"}
    ]
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": post_text}
        ],
        temperature=0.1
    )
    result = response.choices[0].message.content.strip()
    
    if not result:
        logging.warning("Empty response from DeepSeek API.")
        return []

    try:
        return json.loads(result)
    except json.JSONDecodeError:
        logging.error(f"Unable to parse API response: {result}")
        return []

def clean_text(text):
    pattern = r'(?i)\b[a-zA-Z]+\b|\d+(?:\.\d+)?|[$€£₹¥₩]+|\+'
    matches = re.findall(pattern, text)
    return ' '.join(matches)

def get_best_match(noisy_name, choices):
    best_match, _ = process.extractOne(noisy_name, choices)
    return best_match

logging.info(f"Listening for new posts in r/{subreddit_name} containing '{keyword}'...")

for post in subreddit.stream.submissions(skip_existing=True):
    if keyword.lower() in post.title.lower() or keyword.lower() in post.selftext.lower():
        created_utc = post.created_utc
        datetime_post = datetime.utcfromtimestamp(created_utc).strftime('%Y-%m-%d %H:%M:%S')
        
        post_text = f"{post.title} {post.selftext}".strip()
        if post_text:
            try:
                perfumes = parse_perfume_post(post_text)
                if not perfumes:
                    logging.info(f"Skipping post: {post.title} (No perfumes detected)")
                    continue
                
                for perfume in perfumes:
                    perfume_name = get_best_match(perfume.get("Perfume_name", ""), json_df["Perfume_name"].tolist())
                    matched_json = json_df[json_df["Perfume_name"] == perfume_name].iloc[0]
                    
                    new_data = {
                        "post_id": post.id,
                        "link_flair_text": post.link_flair_text,
                        "Perfume_name": perfume_name,
                        "permalink": post.url,
                        "bottle_cost": perfume.get("bottle_cost", ""),
                        "clone_of": matched_json["clone_of"],
                        "official_link": matched_json["official_link"],
                        "official_availability": matched_json["official_availability"],
                        "official_price": matched_json["official_price"]
                    }
                    
                    #f = df.append(new_data, ignore_index=True)
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)

                    logging.info(f"New post added: {post.title}")
            except Exception as e:
                logging.error(f"Error processing post: {e}")
        
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")
