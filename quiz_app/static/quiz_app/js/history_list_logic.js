document.addEventListener('DOMContentLoaded', function() {
    const tableBody = document.getElementById('history-table-body');
    const paginationContainer = document.getElementById('pagination-container');
    // Lấy CSRF token để sử dụng cho các yêu cầu POST (ví dụ: xóa)
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '';

    // Hàm helper để vẽ thanh phân trang đầy đủ
    function renderPaginationControls(data) {
        if (data.total_pages <= 1) {
            return ''; // Không hiển thị gì nếu chỉ có 1 trang
        }

        let html = '';
        const currentPage = data.current_page;
        const totalPages = data.total_pages;

        // Nút "Trang trước"
        html += `<li class="page-item ${data.has_previous ? '' : 'disabled'}">
                    <a class="page-link" href="#" data-page="${data.previous_page_number}">&laquo;</a>
                 </li>`;

        // Logic để hiển thị các số trang và dấu "..."
        const pageWindow = 2; 
        let pagesToShow = [];
        pagesToShow.push(1);
        if (currentPage - pageWindow > 2) {
            pagesToShow.push('...');
        }
        for (let i = Math.max(2, currentPage - pageWindow); i <= Math.min(totalPages - 1, currentPage + pageWindow); i++) {
            pagesToShow.push(i);
        }
        if (currentPage + pageWindow < totalPages - 1) {
            pagesToShow.push('...');
        }
        if (totalPages > 1) {
            pagesToShow.push(totalPages);
        }
        pagesToShow = [...new Set(pagesToShow)];

        pagesToShow.forEach(p => {
            if (p === '...') {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            } else {
                html += `<li class="page-item ${p === currentPage ? 'active' : ''}">
                            <a class="page-link" href="#" data-page="${p}">${p}</a>
                         </li>`;
            }
        });

        // Nút "Trang sau"
        html += `<li class="page-item ${data.has_next ? '' : 'disabled'}">
                    <a class="page-link" href="#" data-page="${data.next_page_number}">&raquo;</a>
                 </li>`;

        return html;
    }


    // Hàm chính để tải dữ liệu lịch sử và vẽ lại bảng
    function fetchAndRenderHistory(page = 1) {
        const url = `?page=${page}`;
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center p-5"><span class="spinner-border spinner-border-sm"></span> Đang tải...</td></tr>';
        
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.json())
        .then(data => {
            tableBody.innerHTML = '';
            if (data.attempts.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center p-5">Bạn chưa hoàn thành bài thi nào.</td></tr>';
            } else {
                data.attempts.forEach(attempt => {
                    const startTime = new Date(attempt.start_time).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
                    // Thêm nút "Xóa" vào mỗi hàng
                    const rowHtml = `
                        <tr>
                            <td><strong>${attempt.quiz_name}</strong></td>
                            <td>${startTime}</td>
                            <td>${attempt.duration}</td>
                            <td>${attempt.score_achieved} / ${attempt.scoring_scale_max}</td>
                            <td class="text-end">
                                <a href="/attempt/${attempt.id}/result/" class="btn btn-sm btn-outline-primary">Xem lại</a>
                                <button type="button" class="btn btn-sm btn-outline-danger ms-2" 
                                        data-bs-toggle="modal" 
                                        data-bs-target="#deleteHistoryModal"
                                        data-delete-url="/attempt/${attempt.id}/delete/">
                                    Xóa
                                </button>
                            </td>
                        </tr>`;
                    tableBody.insertAdjacentHTML('beforeend', rowHtml);
                });
            }
            paginationContainer.innerHTML = renderPaginationControls(data);
        })
        .catch(error => {
            console.error("Lỗi khi tải lịch sử:", error);
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Không thể tải dữ liệu.</td></tr>';
        });
    }

    // Lắng nghe sự kiện click trên các nút phân trang
    paginationContainer.addEventListener('click', function(event) {
        event.preventDefault();
        const targetLink = event.target.closest('a.page-link');
        if (targetLink && targetLink.dataset.page) {
            fetchAndRenderHistory(targetLink.dataset.page);
        }
    });

    // Logic xử lý cho Modal Xóa
    const deleteModalEl = document.getElementById('deleteHistoryModal');
    if (deleteModalEl) {
        let urlToDelete = '';
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

        deleteModalEl.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            urlToDelete = button.dataset.deleteUrl;
        });

        confirmDeleteBtn.addEventListener('click', function() {
            if (urlToDelete) {
                fetch(urlToDelete, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        bootstrap.Modal.getInstance(deleteModalEl).hide();
                        fetchAndRenderHistory(); // Tải lại bảng để cập nhật
                    } else {
                        alert('Lỗi: ' + (data.message || 'Không thể xóa.'));
                    }
                })
                .catch(error => console.error("Lỗi khi thực hiện xóa:", error));
            }
        });
    }

    // Tải dữ liệu cho trang đầu tiên khi trang vừa được mở
    fetchAndRenderHistory(1);
});