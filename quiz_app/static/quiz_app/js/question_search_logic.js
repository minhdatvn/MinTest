document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('questionSearchForm');
    if (!searchForm) return;

    // Lấy URL từ các thuộc tính data-* của form
    const searchUrl = searchForm.dataset.searchUrl;
    const topicsUrl = searchForm.dataset.topicsUrl;

    // --- LOGIC DROPDOWN PHỤ THUỘC ---
    const topicGroupSelect = document.getElementById('id_topic_group');
    const topicSelect = document.getElementById('id_topic');

    if (topicGroupSelect && topicSelect) {
        const resetTopicDropdown = () => {
            topicSelect.innerHTML = '<option value="">Tất cả các Chủ đề</option>';
            topicSelect.disabled = true;
        };

        if (!topicGroupSelect.value) {
            resetTopicDropdown();
        }

        topicGroupSelect.addEventListener('change', function() {
            const groupId = this.value;
            if (!groupId) {
                resetTopicDropdown();
                return;
            }

            topicSelect.disabled = false;
            topicSelect.innerHTML = '<option value="">Đang tải chủ đề...</option>';

            const url = `${topicsUrl}?group_id=${groupId}`; // Dùng biến topicsUrl
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    topicSelect.innerHTML = '<option value="">Tất cả các Chủ đề</option>';
                    if (data.topics) {
                        data.topics.forEach(function(topic) {
                            const option = document.createElement('option');
                            option.value = topic.id;
                            option.textContent = topic.topic_name;
                            topicSelect.appendChild(option);
                        });
                    }
                })
                .catch(error => {
                    console.error('Lỗi khi lấy danh sách chủ đề:', error);
                    resetTopicDropdown();
                });
        });
    }

    // --- LOGIC TÌM KIẾM VÀ PHÂN TRANG BẰNG AJAX ---
    const resultsContainer = document.getElementById('search-results-container');
    
    searchForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(searchForm);
        const searchParams = new URLSearchParams(formData);
        const queryString = searchParams.toString();
        const url = `${searchUrl}?${queryString}`; // Dùng biến searchUrl

        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            resultsContainer.innerHTML = html;
            history.pushState(null, '', url);
        })
        .catch(error => console.error('Lỗi khi tìm kiếm:', error));
    });

    resultsContainer.addEventListener('click', function(event) {
        if (event.target.tagName === 'A' && event.target.classList.contains('page-link')) {
            event.preventDefault();
            const url = event.target.href;
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(response => response.text())
            .then(html => {
                resultsContainer.innerHTML = html;
                history.pushState(null, '', url);
            });
        }
    });

    // --- MODAL XEM CHI TIẾT CÂU HỎI ---
    const detailModal = document.getElementById('questionDetailModal');
    if (detailModal) {
        detailModal.addEventListener('show.bs.modal', function(event) {
            const link = event.relatedTarget;
            const questionId = link.dataset.questionId;
            const modalBody = document.getElementById('questionDetailModalBody');

            modalBody.innerHTML = '<p class="text-center">Đang tải chi tiết...</p>';

            fetch(`/api/question-details/${questionId}/`)
                .then(response => response.json())
                .then(data => {
                    // DEBUG 1: In ra toàn bộ dữ liệu nhận được từ server
                    console.log("--- DEBUG: Dữ liệu nhận được từ server ---");
                    console.log(data);

                    if (data.success) {
                        let contentHtml = `<p><strong>${data.question_text}</strong></p><hr>`;
                        contentHtml += '<ul class="list-group">';

                        data.answers.forEach(answer => {
                            const itemClass = answer.is_correct ? 'list-group-item list-group-item-success' : 'list-group-item';
                            contentHtml += `<li class="${itemClass}">${answer.text}</li>`;
                        });

                        contentHtml += '</ul>';
                        modalBody.innerHTML = contentHtml;
                    } else {
                        modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    }
                })
                .catch(error => {
                    console.error("Lỗi:", error);
                    modalBody.innerHTML = '<div class="alert alert-danger">Không thể tải dữ liệu. Vui lòng thử lại.</div>';
                });
        });
    }
});