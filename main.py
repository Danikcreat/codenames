from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import Optional
import random
import json
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Словари слов
WORDS = {
    "russian": [],
    "english": []
}

# Читаем русские слова
RUSSIAN_WORDS_FILE = "assets/russian-words-caps.txt"
if not os.path.exists(RUSSIAN_WORDS_FILE):
    raise RuntimeError(f"File {RUSSIAN_WORDS_FILE} not found")
with open(RUSSIAN_WORDS_FILE, encoding="utf-8") as f:
    WORDS["russian"] = [line.strip() for line in f if line.strip()]
if len(WORDS["russian"]) < 25:
    raise RuntimeError(f"Not enough words in {RUSSIAN_WORDS_FILE}, found {len(WORDS['russian'])}, need at least 25")

# Читаем английские слова
ENGLISH_WORDS_FILE = "assets/english-words-caps.txt"
if not os.path.exists(ENGLISH_WORDS_FILE):
    raise RuntimeError(f"File {ENGLISH_WORDS_FILE} not found")
with open(ENGLISH_WORDS_FILE, encoding="utf-8") as f:
    WORDS["english"] = [line.strip() for line in f if line.strip()]
if len(WORDS["english"]) < 25:
    raise RuntimeError(f"Not enough words in {ENGLISH_WORDS_FILE}, found {len(WORDS['english'])}, need at least 25")

# Хранилище игр
games = {}

# Стартовый экран
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

# Страница с правилами игры
@app.get("/rules")
async def rules(request: Request, game_id: Optional[str] = None):
    return templates.TemplateResponse("rules.html", {"request": request, "game_id": game_id})

# Создание игры
@app.get("/create-game")
async def create_game(request: Request, first_team: str = "random", language: str = "russian"):
    game_id = str(random.randint(1000, 9999))
    while game_id in games:
        game_id = str(random.randint(1000, 9999))
    
    # Выбираем словарь в зависимости от языка
    if language not in WORDS:
        language = "russian"  # По умолчанию используем русский
    
    words = random.sample(WORDS[language], 25)
    
    # Определяем, какая команда ходит первой
    if first_team == "random":
        first_team = random.choice(["red", "blue"])
    
    # Если первыми ходят красные, то у них 9 карт, у синих 8
    # Если первыми ходят синие, то у них 9 карт, у красных 8
    if first_team == "red":
        red_count = 9
        blue_count = 8
        roles = ["red"] * 9 + ["blue"] * 8 + ["neutral"] * 7 + ["assassin"] * 1
    else:  # first_team == "blue"
        red_count = 8
        blue_count = 9
        roles = ["red"] * 8 + ["blue"] * 9 + ["neutral"] * 7 + ["assassin"] * 1
    
    random.shuffle(roles)
    
    games[game_id] = {
        "words": list(zip(words, roles)),
        "revealed": [False] * 25,
        "players": [],
        "turn": first_team,  
        "red_count": red_count,
        "blue_count": blue_count,
        "game_ended": False,
        "winner": None,
        "language": language
    }
    
    print(f"Created game {game_id} with first team: {first_team}, language: {language}")
    return RedirectResponse(url=f"/game/{game_id}")

# Показ игры
@app.get("/game/{game_id}")
async def show_game(game_id: str, request: Request):
    if game_id not in games:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("index.html", {"request": request, "game_id": game_id})

# API для состояния игры
@app.get("/api/game/{game_id}")
async def get_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return {
        "words": games[game_id]["words"],
        "revealed": games[game_id]["revealed"],
        "turn": games[game_id]["turn"],
        "red_count": games[game_id]["red_count"],
        "blue_count": games[game_id]["blue_count"],
        "game_ended": games[game_id]["game_ended"],
        "winner": games[game_id]["winner"],
        "language": games[game_id].get("language", "russian")  # По умолчанию русский, если не указано
    }

# WebSocket для мультиплеера
@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    if game_id not in games:
        await websocket.close(code=1008, reason="Game not found")
        return
    games[game_id]["players"].append(websocket)
    print(f"Player connected to {game_id}, total players: {len(games[game_id]['players'])}")
    try:
        await websocket.send_json({"type": "connected", "game_id": game_id})
        while True:
            data = await websocket.receive_text()
            print(f"Received WebSocket message in {game_id}: {data}")
            for player in games[game_id]["players"]:
                await player.send_text(data)
    except Exception as e:
        print(f"WebSocket error in {game_id}: {e}")
        games[game_id]["players"].remove(websocket)

# Раскрытие слова
@app.post("/game/{game_id}/reveal/{index}")
async def reveal_word(game_id: str, index: int):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    if not 0 <= index < 25:
        raise HTTPException(status_code=400, detail="Invalid index")
    if games[game_id]["revealed"][index] or games[game_id]["game_ended"]:
        return {"status": "ok"}  # Уже раскрыто или игра окончена
    games[game_id]["revealed"][index] = True
    color = games[game_id]["words"][index][1]
    current_turn = games[game_id]["turn"]

    # Обновляем счёт
    if color == "red":
        games[game_id]["red_count"] -= 1
    elif color == "blue":
        games[game_id]["blue_count"] -= 1

    # Проверяем конец игры
    if games[game_id]["red_count"] == 0:
        games[game_id]["game_ended"] = True
        games[game_id]["winner"] = "red"
    elif games[game_id]["blue_count"] == 0:
        games[game_id]["game_ended"] = True
        games[game_id]["winner"] = "blue"
    elif color == "assassin":
        games[game_id]["game_ended"] = True
        games[game_id]["winner"] = "blue" if current_turn == "red" else "red"  # Противоположная команда выигрывает

    # Логика смены хода
    if not games[game_id]["game_ended"]:
        if (current_turn == "red" and color != "red") or (current_turn == "blue" and color != "blue"):
            games[game_id]["turn"] = "blue" if current_turn == "red" else "red"

    print(f"Revealed word {index} in game {game_id}, color: {color}, turn: {games[game_id]['turn']}, game_ended: {games[game_id]['game_ended']}")
    message = json.dumps({
        "index": index,
        "revealed": True,
        "game_id": game_id,
        "turn": games[game_id]["turn"],
        "red_count": games[game_id]["red_count"],
        "blue_count": games[game_id]["blue_count"],
        "game_ended": games[game_id]["game_ended"],
        "winner": games[game_id]["winner"]
    })
    for player in games[game_id]["players"]:
        try:
            await player.send_text(message)
            print(f"Sent WebSocket message to player in {game_id}: {message}")
        except Exception as e:
            print(f"Failed to send WebSocket message in {game_id}: {e}")
    return {"status": "ok"}

# Передача хода
@app.post("/game/{game_id}/end-turn")
async def end_turn(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    if games[game_id]["game_ended"]:
        return {"status": "ok"}  # Игра уже окончена
    
    # Меняем ход на противоположную команду
    current_turn = games[game_id]["turn"]
    games[game_id]["turn"] = "blue" if current_turn == "red" else "red"
    
    print(f"Turn ended in game {game_id}, new turn: {games[game_id]['turn']}")
    message = json.dumps({
        "game_id": game_id,
        "turn": games[game_id]["turn"],
        "red_count": games[game_id]["red_count"],
        "blue_count": games[game_id]["blue_count"],
        "game_ended": games[game_id]["game_ended"],
        "winner": games[game_id]["winner"],
        "turn_changed": True
    })
    for player in games[game_id]["players"]:
        try:
            await player.send_text(message)
            print(f"Sent WebSocket message to player in {game_id}: {message}")
        except Exception as e:
            print(f"Failed to send WebSocket message in {game_id}: {e}")
    return {"status": "ok"}

# Чтобы запустить сервер на локальном компьютере, выполните следующую команду в терминале:
# uvicorn main:app --reload

# Чтобы запустить сервер для доступа на всех устройсках в сети, выполните следующую команду в терминале:
# uvicorn main:app --host 0.0.0.0 --port 8000 