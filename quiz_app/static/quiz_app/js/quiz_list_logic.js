document.addEventListener("DOMContentLoaded", function () {
    const csrfTokenInput = document.querySelector("[name=csrfmiddlewaretoken]");
    const csrftoken = csrfTokenInput ? csrfTokenInput.value : "";

    if (!csrftoken) {
      console.error("Lỗi: Không tìm thấy CSRF Token trên trang!");
    }

    // --- LOGIC XỬ LÝ MODAL XÓA ĐỀ THI ---
    const deleteModalEl = document.getElementById("deleteQuizModal");
    if (deleteModalEl && csrftoken) {
      const deleteModalInstance = new bootstrap.Modal(deleteModalEl);
      let urlToDelete = "";

      document.body.addEventListener("click", function (event) {
        const deleteButton = event.target.closest(".delete-quiz-btn");
        if (deleteButton) {
          urlToDelete = deleteButton.dataset.deleteUrl;
          deleteModalInstance.show();
        }
      });

      const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
      if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", function () {
          if (urlToDelete) {
            fetch(urlToDelete, {
              method: "POST",
              headers: { "X-CSRFToken": csrftoken },
            })
              .then((response) => response.json())
              .then((data) => {
                if (data.success) {
                  window.location.reload();
                } else {
                  alert("Lỗi: " + (data.message || "Không thể xóa."));
                  deleteModalInstance.hide();
                }
              });
          }
        });
      }
    }

    // --- LOGIC XỬ LÝ MODAL CHIA SẺ ĐỀ THI ---
    const shareModalEl = document.getElementById("shareCodeModal");
    if (shareModalEl && csrftoken) {
      const shareModalInstance = new bootstrap.Modal(shareModalEl);
      const codeDisplay = document.getElementById("access-code-display");
      const spinner = document.getElementById("share-code-spinner");
      const copyBtn = document.getElementById("copy-code-btn");

      document.body.addEventListener("click", function (event) {
        const shareButton = event.target.closest(".share-quiz-btn");
        if (shareButton) {
          const quizId = shareButton.dataset.quizId;
          codeDisplay.textContent = "";
          spinner.style.display = "block";
          copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
          shareModalInstance.show();

          // URL được xây dựng động, không cần template tag
          const url = `/quizzes/${quizId}/generate-code/`; 
          fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": csrftoken },
          })
            .then((response) => response.json())
            .then((data) => {
              spinner.style.display = "none";
              if (data.success) {
                codeDisplay.textContent = data.code;
              } else {
                codeDisplay.textContent = "Lỗi!";
              }
            });
        }
      });

      if (copyBtn) {
        copyBtn.addEventListener("click", function () {
          const code = codeDisplay.textContent;
          if (code && navigator.clipboard) {
            navigator.clipboard.writeText(code).then(() => {
              copyBtn.innerHTML = '<i class="bi bi-clipboard-check-fill text-success"></i>';
              setTimeout(() => {
                copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
              }, 2000);
            });
          }
        });
      }
    }
    
    // KÍCH HOẠT TOOLTIP
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
});