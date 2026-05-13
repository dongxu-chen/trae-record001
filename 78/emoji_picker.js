(function() {
    'use strict';

    var EMOJI_CATEGORIES = {
        '表情': [
            '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
            '🙂', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗',
            '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭',
            '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏',
            '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '🤤',
            '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵',
            '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '😎', '🤓',
            '🧐', '😕', '😟', '🙁', '☹️', '😮', '😯', '😲'
        ],
        '手势': [
            '👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '🤙',
            '👈', '👉', '👆', '🖕', '👇', '☝️', '✋', '🖐️',
            '🖖', '👋', '🤚', '🖕', '✍️', '👏', '🙌', '👐',
            '🤲', '🤝', '🙏', '💪', '🦾', '🦿', '🦵', '🦶'
        ],
        '爱心': [
            '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍',
            '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘',
            '💝', '💟', '♥️', '🫀', '💯', '💢', '💥', '💫',
            '💦', '💨', '🕳️', '💣', '💬', '👁️‍🗨️', '🗨️', '🗯️'
        ],
        '庆祝': [
            '🎉', '🎊', '🎈', '🎁', '🎀', '🏆', '🥇', '🥈',
            '🥉', '⭐', '🌟', '✨', '💫', '🔥', '⚡', '🎯',
            '🎮', '🎲', '🎭', '🎨', '🎬', '🎤', '🎧', '🎼',
            '🎹', '🥁', '🎷', '🎺', '🎸', '🎻', '🪕', '🎯'
        ],
        '食物': [
            '🍕', '🍔', '🍟', '🌭', '🍿', '🧂', '🥓', '🥚',
            '🍳', '🧇', '🥞', '🧈', '🍞', '🥐', '🥖', '🥨',
            '🧀', '🥗', '🍝', '🍜', '🍲', '🍛', '🍣', '🍱',
            '🥟', '🍤', '🍙', '🍚', '🍘', '🍥', '🥠', '🍮'
        ],
        '动物': [
            '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼',
            '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🐔',
            '🐧', '🐦', '🐤', '🦆', '🦅', '🦉', '🦇', '🐺',
            '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🐞'
        ]
    };

    var activeTrigger = null;
    var pickerInstance = null;

    function createPickerContainer() {
        var container = document.createElement('div');
        container.className = 'emoji-picker-container';
        container.id = 'emoji-picker';
        return container;
    }

    function renderCategoryTabs() {
        var tabs = '<div class="emoji-tabs">';
        var first = true;
        for (var category in EMOJI_CATEGORIES) {
            tabs += '<button class="emoji-tab' + (first ? ' active' : '') + '" data-category="' + category + '">' + 
                    category + '</button>';
            first = false;
        }
        tabs += '</div>';
        return tabs;
    }

    function renderEmojiGrid(category) {
        var emojis = EMOJI_CATEGORIES[category] || [];
        var html = '<div class="emoji-grid">';
        for (var i = 0; i < emojis.length; i++) {
            html += '<button class="emoji-btn" data-emoji="' + emojis[i] + '">' + emojis[i] + '</button>';
        }
        html += '</div>';
        return html;
    }

    function createPickerHTML() {
        var firstCategory = Object.keys(EMOJI_CATEGORIES)[0];
        return '<div class="emoji-picker">' +
            '<div class="emoji-picker-header">' +
            '<span>选择表情</span>' +
            '<button class="emoji-picker-close" id="emoji-picker-close">×</button>' +
            '</div>' +
            renderCategoryTabs() +
            '<div class="emoji-content">' +
            renderEmojiGrid(firstCategory) +
            '</div>' +
            '</div>';
    }

    function insertEmojiAtCursor(textarea, emoji) {
        if (!textarea) return;
        
        var start = textarea.selectionStart;
        var end = textarea.selectionEnd;
        var value = textarea.value;
        
        textarea.value = value.substring(0, start) + emoji + value.substring(end);
        textarea.focus();
        var newPos = start + emoji.length;
        textarea.setSelectionRange(newPos, newPos);
        
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function showPicker(textarea, triggerBtn) {
        hidePicker();
        
        activeTrigger = textarea;
        pickerInstance = createPickerContainer();
        pickerInstance.innerHTML = createPickerHTML();
        
        document.body.appendChild(pickerInstance);
        
        positionPicker(pickerInstance, triggerBtn);
        
        bindPickerEvents(pickerInstance, textarea);
    }

    function positionPicker(picker, triggerBtn) {
        var rect = triggerBtn.getBoundingClientRect();
        var pickerRect = { width: 320, height: 350 };
        var viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };
        
        var left = rect.left;
        var top = rect.bottom + 8;
        
        if (left + pickerRect.width > viewport.width - 16) {
            left = viewport.width - pickerRect.width - 16;
        }
        if (left < 16) left = 16;
        
        if (top + pickerRect.height > viewport.height - 16) {
            top = rect.top - pickerRect.height - 8;
            if (top < 16) {
                top = 16;
                picker.style.maxHeight = (viewport.height - 32) + 'px';
            }
        }
        
        picker.style.left = left + 'px';
        picker.style.top = top + 'px';
    }

    function bindPickerEvents(picker, textarea) {
        var tabs = picker.querySelectorAll('.emoji-tab');
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].addEventListener('click', function(e) {
                var category = this.getAttribute('data-category');
                var activeTab = picker.querySelector('.emoji-tab.active');
                if (activeTab) activeTab.classList.remove('active');
                this.classList.add('active');
                
                var content = picker.querySelector('.emoji-content');
                if (content) {
                    content.innerHTML = renderEmojiGrid(category);
                    bindEmojiButtons(content, textarea);
                }
            });
        }
        
        var content = picker.querySelector('.emoji-content');
        if (content) {
            bindEmojiButtons(content, textarea);
        }
        
        var closeBtn = picker.querySelector('#emoji-picker-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', hidePicker);
        }
        
        setTimeout(function() {
            document.addEventListener('click', outsideClickListener);
        }, 0);
    }

    function bindEmojiButtons(container, textarea) {
        var buttons = container.querySelectorAll('.emoji-btn');
        for (var i = 0; i < buttons.length; i++) {
            buttons[i].addEventListener('click', function(e) {
                e.stopPropagation();
                var emoji = this.getAttribute('data-emoji');
                insertEmojiAtCursor(textarea, emoji);
            });
        }
    }

    function outsideClickListener(e) {
        var picker = document.getElementById('emoji-picker');
        if (picker && !picker.contains(e.target)) {
            hidePicker();
        }
    }

    function hidePicker() {
        document.removeEventListener('click', outsideClickListener);
        var picker = document.getElementById('emoji-picker');
        if (picker) {
            picker.remove();
        }
        pickerInstance = null;
        activeTrigger = null;
    }

    window.EmojiPicker = {
        show: function(textarea, triggerElement) {
            showPicker(textarea, triggerElement);
        },

        hide: hidePicker,

        attachToButton: function(button, textarea) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                var existing = document.getElementById('emoji-picker');
                if (existing && activeTrigger === textarea) {
                    hidePicker();
                } else {
                    showPicker(textarea, button);
                }
            });
        },

        insertAtCursor: function(textarea, emoji) {
            insertEmojiAtCursor(textarea, emoji);
        }
    };

})();
