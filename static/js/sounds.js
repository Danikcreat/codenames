/**
 * Звуковое сопровождение для игры Codenames
 */

// Класс для управления звуками
class SoundManager {
    constructor() {
        this.sounds = {};
        this.muted = false;
        this.initialized = false;
        
        // Загружаем настройки из localStorage
        this.loadSettings();
    }
    
    // Инициализация звуков
    init() {
        if (this.initialized) return;
        
        // Определяем звуки для различных событий
        this.registerSound('card_reveal_red', '/static/sounds/click.wav');
        this.registerSound('card_reveal_blue', '/static/sounds/click.wav');
        this.registerSound('card_reveal_neutral', '/static/sounds/click.wav');
        this.registerSound('card_reveal_assassin', '/static/sounds/click.wav');
        this.registerSound('turn_change', '/static/sounds/turn_change.mp3');
        this.registerSound('game_win', '/static/sounds/win.wav');
        this.registerSound('game_lose', '/static/sounds/over.mp3');
        
        // Создаем элемент управления звуком
        this.createSoundControl();
        
        this.initialized = true;
        console.log('Sound manager initialized');
    }
    
    // Регистрация звука
    registerSound(name, path) {
        this.sounds[name] = new Audio(path);
        this.sounds[name].preload = 'auto';
        
        // Обработка ошибок загрузки звуков
        this.sounds[name].onerror = () => {
            console.error(`Failed to load sound: ${path}`);
        };
        
        console.log(`Registered sound: ${name}`);
    }
    
    // Воспроизведение звука
    play(name) {
        if (this.muted || !this.sounds[name]) return;
        
        try {
            // Останавливаем звук, если он уже играет
            this.sounds[name].pause();
            this.sounds[name].currentTime = 0;
            
            // Воспроизводим звук
            this.sounds[name].play().catch(error => {
                console.error(`Error playing sound ${name}:`, error);
            });
        } catch (error) {
            console.error(`Error playing sound ${name}:`, error);
        }
    }
    
    // Включение/выключение звука
    toggleMute() {
        this.muted = !this.muted;
        
        // Обновляем иконку
        const soundIcon = document.getElementById('sound-icon');
        if (soundIcon) {
            soundIcon.textContent = this.muted ? '🔇' : '🔊';
        }
        
        // Сохраняем настройки
        this.saveSettings();
        
        console.log(`Sound ${this.muted ? 'muted' : 'unmuted'}`);
    }
    
    // Создание элемента управления звуком
    createSoundControl() {
        const gameControls = document.querySelector('.game-controls');
        if (!gameControls) return;
        
        const soundButton = document.createElement('button');
        soundButton.id = 'sound-toggle';
        soundButton.className = 'btn sound-btn';
        soundButton.innerHTML = `<span id="sound-icon">${this.muted ? '🔇' : '🔊'}</span>`;
        
        // Добавляем кнопку в начало блока game-controls
        gameControls.insertBefore(soundButton, gameControls.firstChild);
        
        // Добавляем обработчик события
        soundButton.addEventListener('click', () => {
            this.toggleMute();
        });
    }
    
    // Сохранение настроек
    saveSettings() {
        localStorage.setItem('codenames_sound_muted', this.muted);
    }
    
    // Загрузка настроек
    loadSettings() {
        const muted = localStorage.getItem('codenames_sound_muted');
        if (muted !== null) {
            this.muted = muted === 'true';
        }
    }
}

// Создаем глобальный экземпляр менеджера звуков
const soundManager = new SoundManager();

// Инициализируем после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    soundManager.init();
});

// Функция для воспроизведения звука при раскрытии карточки
function playCardSound(color) {
    switch (color) {
        case 'red':
            soundManager.play('card_reveal_red');
            break;
        case 'blue':
            soundManager.play('card_reveal_blue');
            break;
        case 'neutral':
            soundManager.play('card_reveal_neutral');
            break;
        case 'assassin':
            soundManager.play('card_reveal_assassin');
            break;
    }
}

// Функция для воспроизведения звука при смене хода
function playTurnChangeSound() {
    soundManager.play('turn_change');
}

// Функция для воспроизведения звука при окончании игры
function playGameEndSound(isWinner) {
    soundManager.play(isWinner ? 'game_win' : 'game_lose');
}