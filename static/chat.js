
let socket = io();
let currentRoom = 'General';
let username = document.getElementById('username').textContent;
let roomMessages = {};

socket.on('connect', () => {
	joinRoom('General');
	highlightActiveRoom('General');
});

socket.on('message', (data) => {
	addMessage(data.username, data.msg, data.username === username ? 'own' : 'other');
	if (data.username !== username) document.getElementById('notify-sound').play();
});

socket.on('private_message', (data) => {
	addMessage(data.from, `[Private] ${data.msg}`, 'private');
	document.getElementById('notify-sound').play();
});

socket.on('status', (data) => {
	addMessage('System', data.msg, 'system');
});

socket.on('active_users', (data) => {
	const userList = document.getElementById('active-users');
	userList.innerHTML = data.users
		.map((user) => `<div class="user-item" onclick="insertPrivateMessage('${user}')">${user} ${user === username ? '(you)' : ''}</div>`)
		.join('');
});

function addMessage(sender, message, type = 'other') {
    const chat = document.getElementById('chat');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type);

    // 🕒 Add timestamp with spacing
    const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    messageDiv.innerHTML = `<strong>${sender}:</strong> ${message} <span class="time">${time}</span>`;

    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;
}


function sendMessage() {
	const input = document.getElementById('message');
	const message = input.value.trim();
	if (!message) return;

	if (message.startsWith('@')) {
		const [target, ...msgParts] = message.substring(1).split(' ');
		const privateMsg = msgParts.join(' ');
		if (privateMsg) socket.emit('message', { msg: privateMsg, type: 'private', target });
	} else {
		socket.emit('message', { msg: message, room: currentRoom });
	}
	input.value = '';
}

function joinRoom(room) {
	socket.emit('leave', { room: currentRoom });
	currentRoom = room;
	socket.emit('join', { room });
	highlightActiveRoom(room);
	document.getElementById('chat').innerHTML = '';
}

function insertPrivateMessage(user) {
	document.getElementById('message').value = `@${user} `;
	document.getElementById('message').focus();
}

function handleKeyPress(event) {
	if (event.key === 'Enter' && !event.shiftKey) {
		event.preventDefault();
		sendMessage();
	}
}

function highlightActiveRoom(room) {
	document.querySelectorAll('.room-item').forEach((item) => {
		item.classList.remove('active-room');
		if (item.textContent.trim() === room) item.classList.add('active-room');
	});
}

