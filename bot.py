import csv
import random
import streamlit as st

st.set_page_config(page_title="Restaurant Suggester", page_icon="🍽️")

# ------------------------------------------------------------------
# 1. LOAD THE RESTAURANTS FROM THE CSV FILE
# ------------------------------------------------------------------
@st.cache_data
def load_restaurants():
    rows = []
    with open("restaurants.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["price"] = int(row["price"])
            row["moods"] = row["moods"].split(";")
            row["keywords"] = row["keywords"].split()
            rows.append(row)
    return rows


try:
    restaurants = load_restaurants()
except FileNotFoundError:
    st.error("restaurants.csv not found. Run:  python fetch_restaurants.py  first.")
    st.stop()

cities = sorted({r["city"] for r in restaurants})

# ------------------------------------------------------------------
# 2. WORDS THE BOT UNDERSTANDS FOR FEELINGS
# ------------------------------------------------------------------
mood_words = {
    "happy": ["happy", "good", "great", "fine", "amazing", "awesome", "joy", "well"],
    "sad": ["sad", "down", "bad", "depressed", "upset", "cry", "unhappy"],
    "stressed": ["stress", "anxious", "worried", "pressure", "nervous", "busy"],
    "tired": ["tired", "exhausted", "sleepy", "fatigue", "lazy"],
    "romantic": ["romantic", "love", "date", "girlfriend", "boyfriend", "wife", "husband"],
    "celebrating": ["celebrat", "birthday", "party", "success", "graduat", "promotion", "anniversary"],
    "hungry": ["hungry", "starving", "famished"],
    "bored": ["bored", "nothing to do", "boring"],
    "angry": ["angry", "mad", "furious", "annoyed"],
    "lonely": ["lonely", "alone", "miss"],
    "excited": ["excited", "thrilled", "energy", "motivated"],
    "calm": ["calm", "relax", "peace", "quiet", "chill"],
    "social": ["friends", "family", "group", "together"],
}
any_words = ["any", "anything", "all", "everything", "don't know", "dont know", "no idea", "surprise"]


def find_moods(text):
    text = text.lower()
    return [m for m, words in mood_words.items() if any(w in text for w in words)]


def get_budget(text):
    text = text.lower()
    for word, value in {"cheap": 500, "medium": 2000, "expensive": 4000}.items():
        if word in text:
            return value
    digits = "".join(c for c in text if c.isdigit())
    return int(digits) if digits else None


def find_city(text):
    text = text.lower()
    for c in cities:
        if c.lower() in text:
            return c
    return None


def maps_link(r):
    if r.get("maps"):
        return r["maps"]
    return f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lon']}"


def describe(r):
    kind = r["cuisine"] if r["cuisine"] else r["type"].replace("_", " ")
    text = f"**{r['name']}** ({kind}, about {r['price']} DA)\n\n"
    if r["address"]:
        text += f"📍 {r['address']}, {r['city']}\n\n"
    else:
        text += f"📍 {r['city']}\n\n"
    if r["phone"]:
        text += f"📞 {r['phone']}\n\n"
    if r.get("source") == "sample":
        text += f"[🗺️ Find real {kind} places in {r['city']} on Google Maps]({maps_link(r)})\n\n"
    else:
        text += f"[🗺️ Open in Google Maps]({maps_link(r)})\n\n"
    return text


def find_restaurants(city, moods, budget, food):
    results = []
    for r in restaurants:
        if r["city"] != city or r["price"] > budget:
            continue
        if food != "any" and not any(k in food for k in r["keywords"]):
            continue
        score = sum(1 for m in moods if m in r["moods"])
        if r["cuisine"]:
            score += 0.5
        results.append((score, r))
    random.shuffle(results)
    results.sort(key=lambda x: x[0], reverse=True)
    return [r for score, r in results[:5]]


def search_by_name(text):
    text = text.lower().strip()
    if len(text) < 3:
        return []
    return [r for r in restaurants if text in r["name"].lower()][:3]


# ------------------------------------------------------------------
# 3. THE CHAT PAGE
# ------------------------------------------------------------------
st.title("🍽️ Restaurant Suggester")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! 👋 I'm your restaurant buddy. What's your name?"}
    ]
    st.session_state.step = "ask_name"

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_text = st.chat_input("Type your message here...")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    step = st.session_state.step

    if step == "ask_name":
        st.session_state.name = user_text.strip().title()
        st.session_state.step = "ask_city"
        reply = (f"Nice to meet you, {st.session_state.name}! 😊\n\n"
                 f"Which city are you in? ({', '.join(cities)})")

    elif step == "ask_city":
        city = find_city(user_text)
        if city is None:
            reply = f"I only know these cities for now: {', '.join(cities)}. Which one?"
        else:
            st.session_state.city = city
            st.session_state.step = "ask_mood"
            reply = (f"{city}, great choice! 🌆\n\n"
                     "So tell me, how are you feeling today? "
                     "(happy, stressed, tired, sad, romantic, celebrating...)")

    elif step == "ask_mood":
        moods = find_moods(user_text)
        st.session_state.moods = moods
        st.session_state.step = "ask_budget"
        if moods:
            reply = f"I understand, {st.session_state.name}. Let's find the perfect place for you! 💛\n\n"
        else:
            reply = f"Thanks for sharing, {st.session_state.name}! I'll find something nice anyway. 🙂\n\n"
        reply += ("What's your budget per person?\n\n"
                  "- Cheap: around 500 DA\n- Medium: around 2000 DA\n- Expensive: around 4000 DA\n\n"
                  "Type a number (like 1500) or a word (cheap, medium, expensive).")

    elif step == "ask_budget":
        budget = get_budget(user_text)
        if budget is None:
            reply = "I didn't get the budget 😅 Please type a number like 1500, or cheap / medium / expensive."
        else:
            st.session_state.budget = budget
            st.session_state.step = "ask_food"
            reply = (f"Perfect, {budget} DA it is! 💰\n\n"
                     "What do you feel like eating? "
                     "(pizza, tacos, burger, shawarma, sushi, chinese, couscous, grill, cafe, dessert...) "
                     "or type **any**.")

    elif step == "ask_food":
        food = user_text.lower()
        if any(w in food for w in any_words):
            food = "any"
        st.session_state.step = "done"
        matches = find_restaurants(st.session_state.city, st.session_state.moods,
                                   st.session_state.budget, food)
        if matches:
            reply = f"Here is what I suggest for you, {st.session_state.name}: 🎉\n\n"
            for r in matches:
                reply += describe(r)
            reply += ("Type any restaurant name to get its location, "
                      "or click **Start again** for new ideas!")
        else:
            reply = ("Sorry, I found nothing with that budget and food 😢 "
                     "Click **Start again** and try a bigger budget or type **any**.")

    else:  # step == "done": the user can type a restaurant name to get its location
        found = search_by_name(user_text)
        if found:
            reply = "Here is the location: 📍\n\n"
            for r in found:
                reply += describe(r)
        else:
            reply = (f"I couldn't find that name, {st.session_state.name}. "
                     "Try another name or click **Start again** 😊")

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

if st.button("🔄 Start again"):
    st.session_state.clear()
    st.rerun()
