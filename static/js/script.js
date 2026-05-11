// ✅ GLOBAL VARIABLE
let correctAnswer = "";


/* ===============================
   ✅ GENERATE SCENARIO (Button Click)
================================= */
function generateScenario() {

    fetch("/generate-scenario")
    .then(res => res.json())
    .then(data => {

        console.log("SERVER DATA:", data); // Debug

        const scenarioEl = document.getElementById("scenario");
        const optionA = document.getElementById("optionA");
        const optionB = document.getElementById("optionB");
        const optionC = document.getElementById("optionC");

        if (scenarioEl) scenarioEl.innerText = data.scenario;
        if (optionA) optionA.innerText = data.optionA;
        if (optionB) optionB.innerText = data.optionB;
        if (optionC) optionC.innerText = data.optionC;

        // ✅ Safe correctAnswer storage
        correctAnswer = data.correctAnswer || data.correct_answer || "";

        console.log("Stored correct answer:", correctAnswer);

        // ✅ Speak after button click (allowed by browser)
        speakText(data.scenario);

    })
    .catch(error => {
        console.error("Error loading scenario:", error);
    });
}


/* ===============================
   ✅ TEXT TO SPEECH
================================= */
function speakText(text) {

    if (!text) return;

    window.speechSynthesis.cancel();  // Stop previous speech

    const speech = new SpeechSynthesisUtterance(text);
    speech.rate = 0.8;   // Slow for kids
    speech.pitch = 1;
    speech.volume = 1;

    window.speechSynthesis.speak(speech);
}


/* ===============================
   ✅ CHECK ANSWER
================================= */
function checkAnswer(selected) {

    console.log("Selected:", selected);
    console.log("Correct:", correctAnswer);

    if (!correctAnswer) {
        alert("Please generate scenario first");
        return;
    }

    if (selected === correctAnswer) {
        speakText("Very good!");
        alert("Correct!");
    } else {
        speakText("Oops! Try again.");
        alert("Wrong! Try again.");
    }
}


/* ===============================
   ✅ BACKEND EVALUATION (Optional)
================================= */
function evaluateAnswer(answer) {

    fetch('/evaluate-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: answer })
    })
    .then(res => res.json())
    .then(data => {
        if (data.feedback) {
            speakText(data.feedback);
            alert(data.feedback);
        }
    })
    .catch(error => {
        console.error("Error evaluating answer:", error);
    });
}


/* ===============================
   ✅ START VOICE CHAT
================================= */
function startListening() {

    if (!('webkitSpeechRecognition' in window)) {
        alert("Speech Recognition not supported in this browser");
        return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function () {
        console.log("🎤 Listening started...");
    };

    recognition.onerror = function (event) {
        console.log("Speech Error:", event.error);
    };

    recognition.onresult = function (event) {

        const speechText = event.results[0][0].transcript;
        console.log("User said:", speechText);

        const userSpeechEl = document.getElementById("userSpeech");
        if (userSpeechEl) {
            userSpeechEl.innerText = "You said: " + speechText;
        }

        recognition.stop();

        fetch('/ai-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: speechText })
        })
        .then(res => res.json())
        .then(data => {

            const aiReplyEl = document.getElementById("aiReply");

            if (aiReplyEl) {
                aiReplyEl.innerText = "AI: " + data.reply;
            }

            setTimeout(() => {
                speakText(data.reply);
            }, 300);

        })
        .catch(error => {
            console.error("AI Chat error:", error);
        });
    };

    recognition.start();
}