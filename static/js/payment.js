(function () {
  'use strict';

  var config = window.PAYMENT_CONFIG || {};
  var dropzone = document.getElementById('dropzone');
  var fileInput = document.getElementById('screenshot-input');
  var previewWrap = document.getElementById('preview-wrap');
  var previewImg = document.getElementById('preview-img');
  var removeBtn = document.getElementById('remove-preview');
  var uploadBtn = document.getElementById('upload-btn');
  var uploadForm = document.getElementById('upload-form');
  var uploadStatus = document.getElementById('upload-status');
  var otpForm = document.getElementById('otp-form');
  var otpInput = document.getElementById('otp-input');
  var otpStatus = document.getElementById('otp-status');
  var orderIdField = document.getElementById('order-id');
  var panelPay = document.getElementById('panel-pay');
  var panelOtp = document.getElementById('panel-otp');
  var panelSuccess = document.getElementById('panel-success');
  var whatsappLink = document.getElementById('whatsapp-link');
  var steps = document.querySelectorAll('.payment-step');

  var selectedFile = null;

  function setStep(activeStep) {
    steps.forEach(function (step) {
      var num = parseInt(step.getAttribute('data-step'), 10);
      step.classList.remove('is-active', 'is-done');
      if (num < activeStep) step.classList.add('is-done');
      if (num === activeStep) step.classList.add('is-active');
    });
  }

  function showStatus(el, message, type) {
    el.textContent = message;
    el.className = 'payment-form-status' + (type ? ' ' + type : '');
  }

  function clearPreview() {
    selectedFile = null;
    fileInput.value = '';
    previewWrap.hidden = true;
    dropzone.hidden = false;
    dropzone.classList.remove('has-file');
    uploadBtn.disabled = true;
  }

  function showPreview(file) {
    selectedFile = file;
    var reader = new FileReader();
    reader.onload = function (e) {
      previewImg.src = e.target.result;
      previewWrap.hidden = false;
      dropzone.hidden = true;
      dropzone.classList.add('has-file');
      uploadBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  if (dropzone) {
    dropzone.addEventListener('click', function () { fileInput.click(); });

    dropzone.addEventListener('dragover', function (e) {
      e.preventDefault();
      dropzone.classList.add('is-dragover');
    });
    dropzone.addEventListener('dragleave', function () {
      dropzone.classList.remove('is-dragover');
    });
    dropzone.addEventListener('drop', function (e) {
      e.preventDefault();
      dropzone.classList.remove('is-dragover');
      var file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) showPreview(file);
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', function () {
      if (fileInput.files[0]) showPreview(fileInput.files[0]);
    });
  }

  if (removeBtn) removeBtn.addEventListener('click', clearPreview);

  if (uploadForm) {
    uploadForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!selectedFile) return;

      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Uploading…';
      showStatus(uploadStatus, 'Uploading screenshot and sending OTP…', '');

      var formData = new FormData(uploadForm);
      formData.set('screenshot', selectedFile);

      fetch(config.uploadUrl, { method: 'POST', body: formData })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          uploadBtn.disabled = false;
          uploadBtn.textContent = 'Upload & Send OTP';

          if (data.success) {
            orderIdField.value = data.order_id;
            panelPay.hidden = true;
            panelOtp.hidden = false;
            setStep(3);
            showStatus(uploadStatus, '', '');
            otpInput.focus();
          } else {
            showStatus(uploadStatus, data.message || 'Upload failed.', 'error');
          }
        })
        .catch(function () {
          uploadBtn.disabled = false;
          uploadBtn.textContent = 'Upload & Send OTP';
          showStatus(uploadStatus, 'Network error. Please try again.', 'error');
        });
    });
  }

  if (otpForm) {
    otpForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var otp = otpInput.value.trim();
      var orderId = orderIdField.value;

      if (otp.length !== 6) {
        showStatus(otpStatus, 'Please enter the 6-digit OTP.', 'error');
        return;
      }

      var verifyBtn = document.getElementById('verify-btn');
      verifyBtn.disabled = true;
      verifyBtn.textContent = 'Verifying…';
      showStatus(otpStatus, 'Verifying OTP…', '');

      fetch(config.verifyUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId, otp: otp })
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          verifyBtn.disabled = false;
          verifyBtn.textContent = 'Verify OTP';

          if (data.success) {
            panelOtp.hidden = true;
            panelSuccess.hidden = false;
            setStep(4);

            var link = data.whatsapp_link || config.whatsappLink;
            if (link && link !== 'https://chat.whatsapp.com/') {
              whatsappLink.href = link;
            } else {
              whatsappLink.href = '#';
              whatsappLink.addEventListener('click', function (ev) {
                ev.preventDefault();
                alert('WhatsApp group link is not configured yet. Please contact the admin.');
              });
            }
          } else {
            showStatus(otpStatus, data.message || 'Verification failed.', 'error');
          }
        })
        .catch(function () {
          verifyBtn.disabled = false;
          verifyBtn.textContent = 'Verify OTP';
          showStatus(otpStatus, 'Network error. Please try again.', 'error');
        });
    });
  }

  otpInput && otpInput.addEventListener('input', function () {
    otpInput.value = otpInput.value.replace(/\D/g, '').slice(0, 6);
  });
})();
