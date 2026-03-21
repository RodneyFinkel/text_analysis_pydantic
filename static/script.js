const messageContainer = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message to UI
    appendMessage('User', text);
    userInput.value = '';

    // Show a loading state
    const loadingId = appendMessage('Assistant', 'Thinking...');

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await response.json();
        
        // Update the loading message with the actual response
        updateMessage(loadingId, data.response || data.error);
    } catch (error) {
        updateMessage(loadingId, "Error: Could not reach the server.");
    }
}

function appendMessage(sender, text) {
    const div = document.createElement('div');
    const id = Date.now();
    div.id = id;
    div.innerHTML = `<strong>${sender}:</strong> <span>${text}</span>`;
    div.className = sender.toLowerCase();
    messageContainer.appendChild(div);
    messageContainer.scrollTop = messageContainer.scrollHeight;
    return id;
}

function updateMessage(id, newText) {
    const span = document.querySelector(`div[id="${id}"] span`);
    if (span) span.innerText = newText;
}

sendBtn.onclick = sendMessage;
userInput.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };