document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    setupForm(document.querySelector('#createQuestionForm'));
    // ==========================================================
    // ===== HÀM KHỞI TẠO CHO FORMSET (Thêm/Xóa đáp án)    =====
    // ==========================================================
    function initializeAnswerFormset(formElement) {
        if (!formElement || formElement.dataset.initialized === 'true') {
            return;
        }
        formElement.dataset.initialized = 'true';

        // Tìm các thành phần trong form được truyền vào
        const container = formElement.querySelector('.answer-forms-container');
        const addBtn = formElement.querySelector('.add-answer-btn');
        const template = formElement.querySelector('.answer-form-template');
        const totalFormsInput = formElement.querySelector('input[name$="-TOTAL_FORMS"]');
        
        if (!container || !addBtn || !template || !totalFormsInput) {
            return; 
        }

        const maxFormsInput = formElement.querySelector('input[name$="-MAX_NUM_FORMS"]');
        const maxNumForms = maxFormsInput ? parseInt(maxFormsInput.value, 10) : 7;

        // Hàm cập nhật trạng thái nút "Thêm"
        const updateAddButtonVisibility = () => {
            const visibleFormsCount = container.querySelectorAll('.answer-form-row:not(.is-hidden)').length;
            addBtn.style.display = (visibleFormsCount >= maxNumForms) ? 'none' : 'inline-block';
        };

        // Gắn sự kiện cho nút "Thêm đáp án"
        addBtn.addEventListener('click', function() {
            const visibleFormsCount = container.querySelectorAll('.answer-form-row:not(.is-hidden)').length;
            if (visibleFormsCount >= maxNumForms) return;

            const templateHtml = template.innerHTML;
            let formIndex = parseInt(totalFormsInput.value);
            
            const newFormContent = templateHtml.replace(/__prefix__/g, formIndex);
            
            const newFormRow = document.createElement('div');
            newFormRow.className = 'answer-form-row border rounded p-3 mb-3';
            newFormRow.innerHTML = newFormContent;
            
            container.appendChild(newFormRow);
            totalFormsInput.value = formIndex + 1;
            updateAddButtonVisibility();
            renumberAnswerForms(container);
        });

        // Gắn sự kiện cho các nút "Xóa"
        container.addEventListener('click', function(event) {
            if (event.target.classList.contains('remove-answer-btn')) {
                const formRow = event.target.closest('.answer-form-row');
                if (formRow) {
                    // Logic này giờ đúng cho cả đáp án cũ và đáp án mới thêm
                    const deleteInput = formRow.querySelector('input[type="checkbox"][name$="-DELETE"]');
                    if (deleteInput) {
                        deleteInput.checked = true;
                        formRow.classList.add('is-hidden');
                    } else {
                        // Đây là trường hợp dự phòng, sẽ không xảy ra nếu template đúng
                        formRow.remove();
                    }

                    updateAddButtonVisibility();
                    renumberAnswerForms(container);
                }
            }
        });

        updateAddButtonVisibility();
    }
    
    function renumberAnswerForms(container) {
        if (!container) return;
        const visibleForms = container.querySelectorAll('.answer-form-row:not(.is-hidden)');
        visibleForms.forEach((formRow, index) => {
            const numberSpan = formRow.querySelector('.answer-form-number');
            if (numberSpan) {
                numberSpan.textContent = index + 1;
            }
        });
    }

    // === SETUP TỔNG THỂ CHO MỘT FORM ===
    function setupForm(formElement) {
        if (!formElement) return;

        // 1. Khởi tạo các nút Thêm/Xóa
        // Hàm này đã có sẵn guard 'data-initialized' nên an toàn để gọi nhiều lần
        initializeAnswerFormset(formElement);

        // 2. Đánh số lại các đáp án để đảm bảo UI luôn đúng
        const container = formElement.querySelector('.answer-forms-container');
        renumberAnswerForms(container);

        // 3. Cài đặt logic tự động xóa thông báo lỗi
        const errorContainer = formElement.querySelector('#formset-errors');
        if (errorContainer && errorContainer.children.length > 0) {
            const correctCheckboxes = formElement.querySelectorAll('input[type="checkbox"][name$="-is_correct"]');
            
            correctCheckboxes.forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    errorContainer.style.transition = 'opacity 0.5s ease';
                    errorContainer.style.opacity = '0';
                    setTimeout(() => {
                        errorContainer.remove();
                    }, 500);
                }, { once: true });
            });
        }
    }

    // ==========================================================
    // ===== LẮNG NGHE SỰ KIỆN CỦA HTMX                     =====
    // ==========================================================
    // Lắng nghe sự kiện trên toàn bộ trang
    document.body.addEventListener('htmx:afterSwap', function(event) {
        setupForm(document.querySelector('#createQuestionForm'));
        setupForm(document.querySelector('#editQuestionForm'));
    });

    // ==========================================================
    // ===== PHẦN CÒN LẠI (Phân trang và Xóa) GIỮ NGUYÊN    =====
    // ==========================================================
    function renderPaginationControls(data) {
        if (data.total_pages <= 1) return '';
        let html = `<li class="page-item ${data.has_previous ? '' : 'disabled'}"><a class="page-link" href="#" data-page="${data.previous_page_number}">&laquo;</a></li>`;
        const currentPage = data.current_page;
        const totalPages = data.total_pages;
        const pageWindow = 2;
        let pagesToShow = [...new Set([1, ...Array.from({length: Math.min(totalPages, 2*pageWindow + 1)}, (_, i) => Math.max(1, Math.min(totalPages, currentPage - pageWindow + i))), totalPages])];
        
        let lastPage = 0;
        pagesToShow.sort((a, b) => a - b).forEach(p => {
            if (lastPage !== 0 && p > lastPage + 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item ${p === currentPage ? 'active' : ''}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
            lastPage = p;
        });

        html += `<li class="page-item ${data.has_next ? '' : 'disabled'}"><a class="page-link" href="#" data-page="${data.next_page_number}">&raquo;</a></li>`;
        return html;
    }
    
    const tableBody = document.getElementById('questions-table-body');
    const paginationContainer = document.getElementById('pagination-container');
    
    function fetchAndRenderTable(page = 1) {
        const url = `?page=${page}`;
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center p-5"><span class="spinner-border spinner-border-sm"></span> Đang tải...</td></tr>';
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(response => response.json())
            .then(data => {
                tableBody.innerHTML = '';
                if (data.questions.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="4" class="text-center p-5">Chủ đề này chưa có câu hỏi nào.</td></tr>';
                } else {
                    let questionCounter = (data.current_page - 1) * 10 + 1;
                    data.questions.forEach(q => {
                        const rowHtml = `
                            <tr>
                                <th>${questionCounter++}</th>
                                <td style="word-break: break-word;">
                                    <a href="#" class="text-decoration-none text-body-emphasis"
                                    data-bs-toggle="modal"
                                    data-bs-target="#questionDetailModal"
                                    data-question-id="${q.id}">
                                        ${q.text}
                                    </a>
                                </td>
                                <td><span class="badge bg-secondary">${q.type}</span></td>
                                <td class="text-end">
                                    <button type="button" class="btn btn-sm btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#editQuestionModal" hx-get="/question/${q.id}/edit/" hx-target="#edit-modal-body" hx-swap="innerHTML">Sửa</button>
                                    <button type="button" class="btn btn-sm btn-outline-danger ms-1 delete-question-btn" data-delete-url="/question/${q.id}/delete/">Xóa</button>
                                </td>
                            </tr>`;
                        tableBody.insertAdjacentHTML('beforeend', rowHtml);
                    });
                    htmx.process(tableBody);
                }
                paginationContainer.innerHTML = renderPaginationControls(data);
            });
    }

    paginationContainer.addEventListener('click', function(event) {
        event.preventDefault();
        const targetLink = event.target.closest('a.page-link');
        if (targetLink && targetLink.dataset.page) {
            fetchAndRenderTable(targetLink.dataset.page);
        }
    });

    fetchAndRenderTable(1);

    // === LOGIC MỚI VÀ ĐÁNG TIN CẬY ĐỂ XỬ LÝ MODAL XÓA ===
    const questionTableBodyForDelete = document.getElementById('questions-table-body');
    const finalDeleteModalEl = document.getElementById('deleteQuestionModal');

    if (questionTableBodyForDelete && finalDeleteModalEl) {
        const deleteModalInstance = new bootstrap.Modal(finalDeleteModalEl);
        let urlToDelete = '';

        // 1. Lắng nghe click trên toàn bộ bảng
        questionTableBodyForDelete.addEventListener('click', function(event) {
            const deleteButton = event.target.closest('.delete-question-btn');
            if (deleteButton) {
                urlToDelete = deleteButton.dataset.deleteUrl;
                deleteModalInstance.show(); // 2. Hiển thị modal bằng JS
            }
        });

        // 3. Gắn sự kiện cho nút xác nhận
        const confirmDeleteBtn = document.getElementById('confirmDeleteQuestionBtn');
        if(confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', function() {
                if (urlToDelete) {
                    fetch(urlToDelete, {
                        method: 'POST',
                        headers: {'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest'}
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) { 
                            fetchAndRenderTable(); 
                            deleteModalInstance.hide();
                        } else { 
                            alert('Lỗi: ' + data.message); 
                        }
                    });
                }
            });
        }
    }

    // === LOGIC MỚI ĐỂ XỬ LÝ MODAL XEM CHI TIẾT CÂU HỎI ===
    const detailModalEl = document.getElementById('questionDetailModal');
    if (detailModalEl) {
        const modalBody = document.getElementById('questionDetailModalBody');
        detailModalEl.addEventListener('show.bs.modal', function(event) {
            const link = event.relatedTarget;
            const questionId = link.dataset.questionId;

            modalBody.innerHTML = '<div class="text-center p-4"><span class="spinner-border"></span></div>';

            fetch(`/api/question-details/${questionId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        let contentHtml = `<p class="text-body-emphasis fs-5">${data.question_text}</p><hr>`;
                        contentHtml += '<ul class="list-group list-group-flush">';

                        data.answers.forEach(answer => {
                            const itemClass = answer.is_correct 
                                ? 'list-group-item list-group-item-success' 
                                : 'list-group-item';
                            contentHtml += `<li class="${itemClass}">${answer.text}</li>`;
                        });

                        contentHtml += '</ul>';
                        modalBody.innerHTML = contentHtml;
                    } else {
                        modalBody.innerHTML = `<div class="alert alert-danger">${data.error || 'Không thể tải dữ liệu.'}</div>`;
                    }
                })
                .catch(error => {
                    console.error("Lỗi khi tải chi tiết câu hỏi:", error);
                    modalBody.innerHTML = '<div class="alert alert-danger">Lỗi kết nối. Vui lòng thử lại.</div>';
                });
        });
    }
});