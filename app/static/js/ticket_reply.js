document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('replyForm');
    const editor = document.getElementById('replyEditor');
    const hiddenMessage = document.getElementById('replyMessage');
    const wordCount = document.getElementById('replyWordCount');
    const modeInputs = document.querySelectorAll('input[name="reply_type"]');
    const modeSelect = document.getElementById('replyType');
    const modeHint = document.getElementById('replyModeHint');
    const editorWrap = document.getElementById('replyEditorWrap');
    const templateSelect = document.getElementById('replyTemplate');
    const emailFields = document.getElementById('emailFields');
    const internalSubmit = document.getElementById('internalSubmit');
    const attachmentInput = document.getElementById('attachments');
    const attachmentButton = document.getElementById('attachmentButton');
    const attachmentDrop = document.getElementById('attachmentDrop');
    const attachmentList = document.getElementById('attachmentList');
    let plainPaste = false;
    let selectedImage = null;
    const requesterName = window.HELP_DESK_REQUESTER_NAME || 'User';

    if (!form || !editor || !hiddenMessage) return;

    const imagePopover = document.createElement('div');
    imagePopover.className = 'rte-image-resize-popover hidden';
    imagePopover.innerHTML = `
        <button type="button" data-width="25%">Small</button>
        <button type="button" data-width="50%">Medium</button>
        <button type="button" data-width="75%">Large</button>
        <button type="button" data-width="100%">Full</button>
        <button type="button" data-width="custom">Custom</button>
        <button type="button" data-width="">Original</button>
    `;
    document.body.appendChild(imagePopover);

    const escapeHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');

    const updateWordCount = () => {
        const text = editor.innerText.trim();
        const count = text ? text.split(/\s+/).length : 0;
        if (wordCount) wordCount.textContent = `${count} word${count === 1 ? '' : 's'}`;
    };

    const updateToolbarState = () => {
        document.querySelectorAll('#replyEditorWrap [data-command]').forEach((control) => {
            const command = control.dataset.command;
            if (!control.matches('button') || !command) return;
            const activeCommands = ['bold', 'italic', 'underline', 'strikeThrough', 'insertUnorderedList', 'insertOrderedList'];
            if (activeCommands.includes(command)) {
                control.classList.toggle('rte-active', document.queryCommandState(command));
            }
        });
    };

    const syncMessage = () => {
        hiddenMessage.value = editor.innerHTML.trim();
    };

    const normalizeImages = () => {
        editor.querySelectorAll('img').forEach((img) => {
            img.loading = 'lazy';
            img.draggable = false;
            img.title = 'Click to resize image';
            if (!img.style.maxWidth) img.style.maxWidth = '100%';
            if (!img.style.height) img.style.height = 'auto';
        });
    };

    const refreshEditor = () => {
        normalizeImages();
        updateWordCount();
        updateToolbarState();
        syncMessage();
    };

    const hideImagePopover = () => {
        if (selectedImage) selectedImage.classList.remove('rte-image-selected');
        selectedImage = null;
        imagePopover.classList.add('hidden');
    };

    const positionImagePopover = (img) => {
        const rect = img.getBoundingClientRect();
        imagePopover.classList.remove('hidden');
        const top = Math.max(8, rect.top - imagePopover.offsetHeight - 10);
        const left = Math.min(window.innerWidth - imagePopover.offsetWidth - 8, Math.max(8, rect.left));
        imagePopover.style.top = `${top}px`;
        imagePopover.style.left = `${left}px`;
    };

    const selectImage = (img) => {
        hideImagePopover();
        selectedImage = img;
        selectedImage.classList.add('rte-image-selected');
        positionImagePopover(selectedImage);
    };

    const greetingWrapper = () => editor.querySelector('[data-helpdesk-greeting]');

    const greetingHtml = () => (
        `<div data-helpdesk-greeting="1"><p>Dear ${escapeHtml(requesterName)}</p><p>Thank you for your request</p></div><p><br></p>`
    );

    const keepGreetingFirst = () => {
        const wrapper = greetingWrapper();
        if (wrapper && wrapper.previousSibling) editor.insertBefore(wrapper, editor.firstChild);
    };

    const insertGreeting = () => {
        if (!greetingWrapper()) {
            editor.insertAdjacentHTML('afterbegin', greetingHtml());
        }
        keepGreetingFirst();
    };

    const removeGreeting = () => {
        const wrapper = greetingWrapper();
        if (!wrapper) return;
        const spacer = wrapper.nextElementSibling;
        wrapper.remove();
        if (spacer && spacer.innerText.trim() === '' && spacer.tagName === 'P') spacer.remove();
        refreshEditor();
    };

    const setMode = (mode) => {
        editorWrap.classList.toggle('reply-internal-mode', mode === 'internal');
        editorWrap.classList.toggle('reply-email-mode', mode === 'email');
        if (emailFields) emailFields.classList.toggle('hidden', mode !== 'email');
        if (modeHint) {
            if (mode === 'internal') {
                modeHint.textContent = 'Internal notes are visible only to the support team.';
            } else if (mode === 'email') {
                modeHint.textContent = 'Email replies are public and sent as ticket communication.';
            } else {
                modeHint.textContent = 'Public replies are visible to the requester.';
            }
        }
        if (mode === 'internal') {
            removeGreeting();
        } else {
            insertGreeting();
            keepGreetingFirst();
            refreshEditor();
        }
    };

    const selectedMode = () => {
        const checked = document.querySelector('input[name="reply_type"]:checked');
        if (checked) return checked.value;
        return modeSelect ? modeSelect.value : 'public';
    };

    const insertTable = () => {
        const rows = Math.max(1, Math.min(8, parseInt(window.prompt('Rows:', '3') || '3', 10)));
        const cols = Math.max(1, Math.min(6, parseInt(window.prompt('Columns:', '3') || '3', 10)));
        let html = '<table class="rte-table"><tbody>';
        for (let r = 0; r < rows; r += 1) {
            html += '<tr>';
            for (let c = 0; c < cols; c += 1) html += '<td><br></td>';
            html += '</tr>';
        }
        html += '</tbody></table><p><br></p>';
        document.execCommand('insertHTML', false, html);
    };

    const applyFontSize = (size) => {
        if (!size) return;
        document.execCommand('fontSize', false, '7');
        editor.querySelectorAll('font[size="7"]').forEach((node) => {
            const span = document.createElement('span');
            span.style.fontSize = size;
            span.innerHTML = node.innerHTML;
            node.replaceWith(span);
        });
    };

    const insertImage = () => {
        const url = window.prompt('Image URL:', 'https://');
        if (!url || !/^https?:\/\//i.test(url)) return;
        const alt = window.prompt('Alt text:', '') || '';
        const safeUrl = url.replace(/"/g, '&quot;');
        const safeAlt = alt.replace(/"/g, '&quot;');
        document.execCommand('insertHTML', false, `<img src="${safeUrl}" alt="${safeAlt}" style="max-width:100%;height:auto;">`);
        normalizeImages();
    };

    imagePopover.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-width]');
        if (!button || !selectedImage) return;
        let width = button.dataset.width;
        if (width === 'custom') {
            const input = window.prompt('Image width (% or px):', parseInt(selectedImage.style.width, 10) || 50);
            if (!input) return;
            width = /^\d+$/.test(input.trim()) ? `${input.trim()}%` : input.trim();
        }
        if (!width) {
            selectedImage.style.width = '';
            selectedImage.style.maxWidth = '100%';
        } else {
            selectedImage.style.width = width;
            selectedImage.style.maxWidth = '100%';
        }
        selectedImage.style.height = 'auto';
        refreshEditor();
        positionImagePopover(selectedImage);
    });

    document.querySelectorAll('#replyEditorWrap [data-command]').forEach((control) => {
        const runCommand = () => {
            const command = control.dataset.command;
            let value = control.dataset.value || control.value || null;
            editor.focus();
            if (command === 'createLink') {
                value = window.prompt('Enter link URL');
                if (!value) return;
            }
            if (command === 'fontSizePx') {
                applyFontSize(value);
            } else if (command === 'table') {
                insertTable();
            } else if (command === 'image') {
                insertImage();
            } else if (command === 'checklist') {
                document.execCommand('insertHTML', false, '<ul class="rte-checklist"><li><input type="checkbox"> Action item</li><li><input type="checkbox"> Follow up</li></ul>');
            } else if (command === 'codeBlock') {
                document.execCommand('formatBlock', false, 'pre');
            } else if (command === 'plainPaste') {
                plainPaste = !plainPaste;
                control.classList.toggle('rte-active', plainPaste);
            } else {
                document.execCommand(command, false, value);
            }
            if (control.tagName === 'SELECT') control.value = command === 'formatBlock' ? value : '';
            refreshEditor();
        };
        control.addEventListener(control.matches('input[type="color"], select') ? 'change' : 'click', runCommand);
    });

    modeInputs.forEach((input) => {
        input.addEventListener('change', () => setMode(input.value));
    });
    if (modeSelect) {
        modeSelect.addEventListener('change', () => setMode(modeSelect.value));
    }

    if (internalSubmit) {
        internalSubmit.addEventListener('click', () => {
            const internalMode = document.querySelector('input[name="reply_type"][value="internal"]');
            if (internalMode) {
                internalMode.checked = true;
                setMode('internal');
            } else if (modeSelect) {
                modeSelect.value = 'internal';
                setMode('internal');
            }
        });
    }

    if (templateSelect) {
        templateSelect.addEventListener('change', () => {
            const option = templateSelect.selectedOptions[0];
            if (!option || !option.dataset.body) return;
            editor.innerHTML = option.dataset.body;
            if (option.dataset.internal === '1') {
                const internalMode = document.querySelector('input[name="reply_type"][value="internal"]');
                if (internalMode) internalMode.checked = true;
                if (modeSelect) modeSelect.value = 'internal';
                setMode('internal');
            }
            refreshEditor();
            if (selectedMode() !== 'internal') {
                insertGreeting();
            }
            editor.focus();
        });
    }

    const renderAttachments = () => {
        if (!attachmentInput || !attachmentList) return;
        attachmentList.innerHTML = '';
        Array.from(attachmentInput.files).forEach((file) => {
            const pill = document.createElement('span');
            pill.className = 'attachment-pill';
            const size = file.size < 1024 * 1024 ? `${(file.size / 1024).toFixed(1)} KB` : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
            pill.innerHTML = `<i class="fas fa-paperclip"></i><span class="truncate max-w-[180px]"></span><span class="text-gray-400">${size}</span>`;
            pill.querySelector('span').textContent = file.name;
            attachmentList.appendChild(pill);
        });
    };

    if (attachmentButton && attachmentInput) {
        attachmentButton.addEventListener('click', () => attachmentInput.click());
        attachmentInput.addEventListener('change', renderAttachments);
    }

    if (attachmentDrop && attachmentInput) {
        ['dragenter', 'dragover'].forEach((eventName) => {
            attachmentDrop.addEventListener(eventName, (event) => {
                event.preventDefault();
                attachmentDrop.classList.add('attachment-drop-active');
            });
        });
        ['dragleave', 'drop'].forEach((eventName) => {
            attachmentDrop.addEventListener(eventName, (event) => {
                event.preventDefault();
                attachmentDrop.classList.remove('attachment-drop-active');
            });
        });
        attachmentDrop.addEventListener('drop', (event) => {
            attachmentInput.files = event.dataTransfer.files;
            renderAttachments();
        });
    }

    editor.addEventListener('input', () => {
        if (selectedMode() !== 'internal') {
            keepGreetingFirst();
        }
        refreshEditor();
    });
    editor.addEventListener('click', (event) => {
        const image = event.target.closest('img');
        if (image && editor.contains(image)) {
            event.preventDefault();
            selectImage(image);
            return;
        }
        hideImagePopover();
    });
    document.addEventListener('click', (event) => {
        if (!editor.contains(event.target) && !imagePopover.contains(event.target)) {
            hideImagePopover();
        }
    });
    window.addEventListener('scroll', () => {
        if (selectedImage) positionImagePopover(selectedImage);
    }, true);
    window.addEventListener('resize', () => {
        if (selectedImage) positionImagePopover(selectedImage);
    });
    editor.addEventListener('mouseup', updateToolbarState);
    editor.addEventListener('keyup', updateToolbarState);
    editor.addEventListener('keydown', (event) => {
        if (event.key === 'Tab') {
            event.preventDefault();
            document.execCommand(event.shiftKey ? 'outdent' : 'indent', false, null);
            refreshEditor();
        }
    });
    editor.addEventListener('paste', (event) => {
        if (plainPaste) {
            event.preventDefault();
            const text = (event.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, text);
            if (selectedMode() !== 'internal') {
                keepGreetingFirst();
            }
            refreshEditor();
            return;
        }
        setTimeout(() => {
            if (selectedMode() !== 'internal') {
                keepGreetingFirst();
            }
            refreshEditor();
        }, 0);
    });

    form.addEventListener('submit', (event) => {
        if (selectedMode() !== 'internal') {
            keepGreetingFirst();
        }
        syncMessage();
        const text = editor.innerText.trim();
        if (!text) {
            event.preventDefault();
            editor.focus();
            editorWrap.classList.add('reply-editor-error');
            setTimeout(() => editorWrap.classList.remove('reply-editor-error'), 1600);
        }
    });

    setMode(selectedMode());
    refreshEditor();
});
