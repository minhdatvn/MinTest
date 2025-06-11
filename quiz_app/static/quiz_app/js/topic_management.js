document.addEventListener('DOMContentLoaded', function() {
    // --- PHẦN 1: HÀM HELPER VÀ BIẾN TOÀN CỤC ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    let createGroupUrl = '';
    let createTopicUrl = '';
    let urlToDelete = '';
    let editGroupUrl = '';
    let editTopicUrl = '';

    // --- PHẦN 2: LOGIC XỬ LÝ CÁC MODAL ---

    // A. MODAL TẠO NHÓM MỚI
    const createGroupModalEl = document.getElementById('createGroupModal');
    if (createGroupModalEl) {
        const saveNewGroupBtn = document.getElementById('saveNewGroupBtn');
        createGroupModalEl.addEventListener('show.bs.modal', function(event) {
            createGroupUrl = event.relatedTarget.getAttribute('data-create-url');
        });
        saveNewGroupBtn.addEventListener('click', function() {
            const groupName = document.getElementById('newGroupName').value.trim();
            const groupDesc = document.getElementById('newGroupDescription').value.trim();
            if (groupName === '' || !createGroupUrl) return;

            fetch(createGroupUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({ 'group_name': groupName, 'group_description': groupDesc })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) { window.location.reload(); } 
                else { alert('Lỗi: ' + JSON.stringify(data.errors)); }
            });
        });
    }

    // B. MODAL TẠO CHỦ ĐỀ MỚI
    const createTopicModalEl = document.getElementById('createTopicModal');
    if (createTopicModalEl) {
        const saveNewTopicBtn = document.getElementById('saveNewTopicBtn');
        createTopicModalEl.addEventListener('show.bs.modal', function(event) {
            createTopicUrl = event.relatedTarget.getAttribute('data-create-url');
        });
        saveNewTopicBtn.addEventListener('click', function() {
            const topicName = document.getElementById('newTopicName').value.trim();
            const topicDesc = document.getElementById('newTopicDescription').value.trim();
            const groupId = document.getElementById('topicGroupSelect').value;
            if (topicName === '' || !createTopicUrl) return;

            fetch(createTopicUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({ 'topic_name': topicName, 'description': topicDesc, 'group': groupId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) { window.location.reload(); } 
                else { alert('Lỗi: ' + JSON.stringify(data.errors)); }
            });
        });
    }
    
    // C. MODAL XÁC NHẬN XÓA (CÓ XỬ LÝ ENTER)
    const deleteConfirmModalEl = document.getElementById('deleteConfirmModal');
    if (deleteConfirmModalEl) {
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

        deleteConfirmModalEl.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            urlToDelete = button.getAttribute('data-delete-url');
            const modalBody = deleteConfirmModalEl.querySelector('.modal-body');

            if (button.classList.contains('delete-topic-btn')) {
                const topicName = button.getAttribute('data-topic-name');
                modalBody.innerHTML = `Bạn có chắc chắn muốn xóa chủ đề <strong>"${topicName}"</strong>? <br><small class="text-danger">Tất cả câu hỏi bên trong cũng sẽ bị xóa.</small>`;
            } else if (button.classList.contains('delete-group-btn')) {
                const groupName = button.getAttribute('data-group-name');
                modalBody.innerHTML = `Bạn có chắc chắn muốn xóa nhóm chủ đề <strong>"${groupName}"</strong>? <p class="text-muted small mt-2">Các chủ đề con sẽ được chuyển vào nhóm mặc định.</p>`;
            }
        });

        confirmDeleteBtn.addEventListener('click', function() {
            if (!urlToDelete) return;
            fetch(urlToDelete, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) { window.location.reload(); }
                else { alert('Lỗi: ' + data.message); }
            });
        });

        const handleDeleteEnter = (event) => {
            if (event.key === 'Enter') {
                confirmDeleteBtn.click();
            }
        };
        deleteConfirmModalEl.addEventListener('shown.bs.modal', () => {
            document.addEventListener('keyup', handleDeleteEnter);
        });
        deleteConfirmModalEl.addEventListener('hidden.bs.modal', () => {
            document.removeEventListener('keyup', handleDeleteEnter);
        });
    }

    // D. MODAL SỬA NHÓM CHỦ ĐỀ
    const editGroupModalEl = document.getElementById('editGroupModal');
    if (editGroupModalEl) {
        const updateGroupBtn = document.getElementById('updateGroupBtn');
        const editGroupNameInput = document.getElementById('editGroupName');
        const editGroupDescInput = document.getElementById('editGroupDescription');
        
        editGroupModalEl.addEventListener('show.bs.modal', function(event) {
            editGroupUrl = event.relatedTarget.getAttribute('data-group-url');
            fetch(editGroupUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(res => res.json())
                .then(data => {
                    editGroupNameInput.value = data.name;
                    editGroupDescInput.value = data.description;
                });
        });

        updateGroupBtn.addEventListener('click', function() {
            const updatedData = {
                group_name: editGroupNameInput.value.trim(),
                group_description: editGroupDescInput.value.trim(),
            };
            if(updatedData.group_name === '' || !editGroupUrl) return;

            fetch(editGroupUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify(updatedData)
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) { window.location.reload(); }
                else { alert('Lỗi: ' + JSON.stringify(data.errors)); }
            });
        });
    }

    // E. MODAL SỬA CHỦ ĐỀ
    const editTopicModalEl = document.getElementById('editTopicModal');
    if (editTopicModalEl) {
        const updateTopicBtn = document.getElementById('updateTopicBtn');
        const editTopicNameInput = document.getElementById('editTopicName');
        const editTopicDescInput = document.getElementById('editTopicDescription');

        editTopicModalEl.addEventListener('show.bs.modal', function(event) {
            editTopicUrl = event.relatedTarget.getAttribute('data-topic-url');
            fetch(editTopicUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(res => res.json())
                .then(data => {
                    editTopicNameInput.value = data.name;
                    editTopicDescInput.value = data.description;
                });
        });

        updateTopicBtn.addEventListener('click', function() {
            const updatedData = {
                topic_name: editTopicNameInput.value.trim(),
                description: editTopicDescInput.value.trim(),
            };
            if(updatedData.topic_name === '' || !editTopicUrl) return;

            fetch(editTopicUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify(updatedData)
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) { window.location.reload(); }
                else { alert('Lỗi: ' + JSON.stringify(data.errors)); }
            });
        });
    }
});