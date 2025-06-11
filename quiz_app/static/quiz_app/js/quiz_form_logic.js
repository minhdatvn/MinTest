document.addEventListener('DOMContentLoaded', function() {
    // --- PHẦN 1: LOGIC CHUNG VÀ CHUYỂN ĐỔI PANEL ---
    const mainForm = document.querySelector('form[method="post"]');
    if (!mainForm) return;

    const staticPanel = document.getElementById('static-quiz-panel');
    const dynamicPanel = document.getElementById('dynamic-quiz-panel');
    const quizTypeRadios = document.querySelectorAll('input[name="quiz_type"]');
    const staticActions = document.getElementById('static-quiz-actions');
    const dynamicActions = document.getElementById('dynamic-quiz-actions');

    function togglePanels() {
        // Đảm bảo các phần tử tồn tại trước khi thao tác
        if (!staticPanel || !dynamicPanel || !staticActions || !dynamicActions) return;

        const selectedType = document.querySelector('input[name="quiz_type"]:checked').value;

        if (selectedType === 'static') {
            // Dùng classList để thêm/xóa class 'd-none'
            staticPanel.classList.remove('d-none');
            dynamicPanel.classList.add('d-none');
            staticActions.classList.remove('d-none');
            dynamicActions.classList.add('d-none');
        } else if (selectedType === 'dynamic') {
            staticPanel.classList.add('d-none');
            dynamicPanel.classList.remove('d-none');
            staticActions.classList.add('d-none');
            dynamicActions.classList.remove('d-none');
        }
    }

    if (quizTypeRadios.length > 0) {
        quizTypeRadios.forEach(radio => radio.addEventListener('change', togglePanels));
        togglePanels();
    }
           
    // === PHẦN 2: LOGIC CHO BỘ ĐẾM VÀ CHECKBOX "CHỌN TẤT CẢ" ===
    const countSpan = document.getElementById('selected-question-count');
    const allQuestionCheckboxes = document.querySelectorAll('.question-checkbox');
    const groupSelectAllCheckboxes = document.querySelectorAll('.group-select-all');
    const topicSelectAllCheckboxes = document.querySelectorAll('.topic-select-all');

    // HÀM CẬP NHẬT BỘ ĐẾM (KHÔNG ĐỔI)
    function updateSelectedCount() {
        const selectedCount = document.querySelectorAll('.question-checkbox:checked').length;
        if (countSpan) countSpan.textContent = selectedCount;
    }

    // HÀM MỚI: Cập nhật trạng thái checkbox của CHỦ ĐỀ
    function updateTopicSelectAllState(topicId) {
        const masterCheckbox = document.querySelector(`.topic-select-all[data-topic-id="${topicId}"]`);
        const childCheckboxes = document.querySelectorAll(`.question-checkbox[data-topic-id="${topicId}"]`);
        if (!masterCheckbox || childCheckboxes.length === 0) return;

        const total = childCheckboxes.length;
        const checkedCount = document.querySelectorAll(`.question-checkbox[data-topic-id="${topicId}"]:checked`).length;

        if (checkedCount === 0) {
            masterCheckbox.checked = false;
            masterCheckbox.indeterminate = false;
        } else if (checkedCount === total) {
            masterCheckbox.checked = true;
            masterCheckbox.indeterminate = false;
        } else {
            masterCheckbox.checked = false;
            masterCheckbox.indeterminate = true;
        }
    }

    // HÀM CẬP NHẬT TRẠNG THÁI CHECKBOX CỦA NHÓM
    function updateGroupSelectAllState(groupId) {
        const masterCheckbox = document.querySelector(`.group-select-all[data-group-id="${groupId}"]`);
        const childCheckboxes = document.querySelectorAll(`.question-checkbox[data-group-id="${groupId}"]`);
        if (!masterCheckbox || childCheckboxes.length === 0) return;

        const total = childCheckboxes.length;
        const checkedCount = document.querySelectorAll(`.question-checkbox[data-group-id="${groupId}"]:checked`).length;

        if (checkedCount === 0) {
            masterCheckbox.checked = false;
            masterCheckbox.indeterminate = false;
        } else if (checkedCount === total) {
            masterCheckbox.checked = true;
            masterCheckbox.indeterminate = false;
        } else {
            masterCheckbox.checked = false;
            masterCheckbox.indeterminate = true;
        }
    }

    // SỰ KIỆN KHI BẤM VÀO CHECKBOX "CHỌN TẤT CẢ" CỦA NHÓM (CẬP NHẬT)
    groupSelectAllCheckboxes.forEach(masterCheckbox => {
        masterCheckbox.addEventListener('change', function() {
            const groupId = this.dataset.groupId;
            const isChecked = this.checked;
            // Chọn tất cả các câu hỏi con
            document.querySelectorAll(`.question-checkbox[data-group-id="${groupId}"]`)
                    .forEach(child => child.checked = isChecked);
            // Cập nhật luôn trạng thái của các checkbox chủ đề con
            document.querySelectorAll(`.topic-select-all[data-group-id="${groupId}"]`)
                    .forEach(topicMaster => {
                        topicMaster.checked = isChecked;
                        topicMaster.indeterminate = false;
                    });
            updateSelectedCount();
        });
    });

    // SỰ KIỆN MỚI: KHI BẤM VÀO CHECKBOX "CHỌN TẤT CẢ" CỦA CHỦ ĐỀ
    topicSelectAllCheckboxes.forEach(topicMasterCheckbox => {
        topicMasterCheckbox.addEventListener('change', function() {
            const topicId = this.dataset.topicId;
            const groupId = this.dataset.groupId;
            const isChecked = this.checked;
            document.querySelectorAll(`.question-checkbox[data-topic-id="${topicId}"]`)
                    .forEach(child => child.checked = isChecked);
            updateSelectedCount();
            updateGroupSelectAllState(groupId); // Cập nhật lại checkbox của nhóm cha
        });
    });

    // SỰ KIỆN KHI BẤM VÀO TỪNG CÂU HỎI (CẬP NHẬT)
    allQuestionCheckboxes.forEach(childCheckbox => {
        childCheckbox.addEventListener('change', function() {
            const groupId = this.dataset.groupId;
            const topicId = this.dataset.topicId;
            updateTopicSelectAllState(topicId); // Cập nhật checkbox chủ đề
            updateGroupSelectAllState(groupId); // Cập nhật checkbox nhóm
            updateSelectedCount();
        });
    });

    // Khởi tạo trạng thái đúng khi tải trang
    if (staticPanel) {
        updateSelectedCount();
        topicSelectAllCheckboxes.forEach(master => updateTopicSelectAllState(master.dataset.topicId));
        groupSelectAllCheckboxes.forEach(master => updateGroupSelectAllState(master.dataset.groupId));
    }
});