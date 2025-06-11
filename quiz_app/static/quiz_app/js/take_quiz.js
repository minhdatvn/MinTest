document.addEventListener('DOMContentLoaded', function () {
    const quizForm = document.getElementById('quiz-form');
    if (!quizForm) return;

    // --- KHAI BÁO BIẾN DÙNG CHUNG ---
    const attemptId = quizForm.dataset.attemptId;
    const storageKey = `quizAttempt_${attemptId}`;
    const questionContainers = document.querySelectorAll('.question-container');
    const navBoxes = document.querySelectorAll('.question-nav-box');
    const nextBtn = document.getElementById('next-question-btn');
    const prevBtn = document.getElementById('prev-question-btn');
    const questionsWrapper = document.getElementById('questions-wrapper');
    const totalQuestions = questionContainers.length;
    let currentQuestionIndex = 0;

    // --- CÁC HÀM XỬ LÝ CHÍNH ---
    function showQuestion(index) {
        if(index < 0 || index >= totalQuestions) return;
        currentQuestionIndex = index;

        questionContainers.forEach((container, i) => {
            container.classList.toggle('d-none', i !== index);
        });
        navBoxes.forEach((box, i) => {
            box.classList.toggle('active', i === index);
        });

        if(prevBtn) prevBtn.disabled = (index === 0);
        if(nextBtn) nextBtn.disabled = (index === totalQuestions - 1);
        
        saveState();
    }

    function saveState() {
        const state = { answers: {}, flags: [], currentIndex: currentQuestionIndex };
        document.querySelectorAll('.answer-input:checked').forEach(input => {
            const name = input.name;
            if (!state.answers[name]) { state.answers[name] = []; }
            state.answers[name].push(input.value);
        });
        document.querySelectorAll('.flag-btn.flagged').forEach(btn => {
            state.flags.push(btn.dataset.questionIndex);
        });
        localStorage.setItem(storageKey, JSON.stringify(state));
    }

    function loadState() {
        const savedStateJSON = localStorage.getItem(storageKey);
        if (!savedStateJSON) { showQuestion(0); return; }
        const state = JSON.parse(savedStateJSON);
        for (const questionName in state.answers) {
            state.answers[questionName].forEach(value => {
                const input = document.querySelector(`input[name="${questionName}"][value="${value}"]`);
                if (input) {
                    input.checked = true;
                    const qIndex = input.dataset.questionIndex;
                    const navBox = document.querySelector(`.question-nav-box[data-question-index="${qIndex}"]`);
                    if(navBox) navBox.classList.add('answered');
                }
            });
        }
        state.flags.forEach(index => {
            const flagBtn = document.querySelector(`.flag-btn[data-question-index="${index}"]`);
            const navBox = document.querySelector(`.question-nav-box[data-question-index="${index}"]`);
            if (flagBtn) flagBtn.classList.add('flagged');
            if (navBox) navBox.classList.add('flagged');
        });
        showQuestion(state.currentIndex || 0);
    }

    function clearState() { localStorage.removeItem(storageKey); }

    // --- GẮN CÁC SỰ KIỆN ---
    const beforeUnloadHandler = (event) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', beforeUnloadHandler);

    quizForm.addEventListener('submit', function() {
        window.removeEventListener('beforeunload', beforeUnloadHandler);
        clearState();
    });

    const timerDisplay = document.getElementById('timer-display');
    if (timerDisplay) {
        let timeInSeconds = parseInt(timerDisplay.dataset.remainingSeconds, 10);
        if (!isNaN(timeInSeconds) && timeInSeconds > 0) {
            let timerInterval = setInterval(() => {
                if (timeInSeconds <= 0) {
                    clearInterval(timerInterval);
                    alert('Đã hết thời gian làm bài! Bài của bạn sẽ được tự động nộp.');
                    window.removeEventListener('beforeunload', beforeUnloadHandler);
                    clearState();
                    quizForm.submit();
                    return;
                }
                timeInSeconds--;
                const minutes = String(Math.floor(timeInSeconds / 60)).padStart(2, '0');
                const seconds = String(timeInSeconds % 60).padStart(2, '0');
                timerDisplay.innerHTML = `<i class="bi bi-clock"></i> ${minutes}:${seconds}`;
            }, 1000);
        }
    }

    if(nextBtn) nextBtn.addEventListener('click', () => showQuestion(currentQuestionIndex + 1));
    if(prevBtn) prevBtn.addEventListener('click', () => showQuestion(currentQuestionIndex - 1));
    navBoxes.forEach(box => {
        box.addEventListener('click', function () {
            showQuestion(parseInt(this.dataset.questionIndex, 10));
        });
    });

    if (questionsWrapper) {
        questionsWrapper.addEventListener('click', function(event) {
            let stateShouldBeSaved = false;
            if (event.target.closest('.flag-btn')) {
                const flagButton = event.target.closest('.flag-btn');
                const questionIndex = flagButton.dataset.questionIndex;
                const navBox = document.querySelector(`.question-nav-box[data-question-index="${questionIndex}"]`);
                flagButton.classList.toggle('flagged');
                if (navBox) navBox.classList.toggle('flagged');
                stateShouldBeSaved = true;
            }
            if (event.target.closest('.answer-input')) {
                const answerInput = event.target.closest('.answer-input');
                const questionIndex = answerInput.dataset.questionIndex;
                const navBox = document.querySelector(`.question-nav-box[data-question-index="${questionIndex}"]`);
                if(navBox) navBox.classList.add('answered');
                stateShouldBeSaved = true;
            }
            if (stateShouldBeSaved) saveState();
        });
    }

    const submitConfirmModalEl = document.getElementById('submitConfirmModal');
    if (submitConfirmModalEl) {
        const submitConfirmModal = new bootstrap.Modal(submitConfirmModalEl);
        const unansweredCountSpan = document.getElementById('unanswered-count');
        const confirmSubmitBtn = document.getElementById('confirmSubmitBtn');

        quizForm.addEventListener('submit', function(event) {
            let unansweredCount = 0;
            questionContainers.forEach(container => {
                if (!container.querySelector('input[type="radio"]:checked, input[type="checkbox"]:checked')) {
                    unansweredCount++;
                }
            });
            if (unansweredCount > 0) {
                event.preventDefault(); 
                unansweredCountSpan.textContent = unansweredCount;
                submitConfirmModal.show();
            }
        });
        if(confirmSubmitBtn) {
            confirmSubmitBtn.addEventListener('click', function() {
                quizForm.submit();
            });
        }
    }

    // --- KHỞI TẠO ---
    loadState();
});