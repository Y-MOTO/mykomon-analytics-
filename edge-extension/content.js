// content.js
// MyKomonの日報入力画面にフローティングUIを表示する

(function () {
  var floatingUI = null;
  var triggerBtn = null;
  var isUIVisible = false;
  var initialized = false;

  var state = {
    category: null,
    status: null,
    process: null,
    blocking: [],
    urgency: null,
    workload: null
  };

  function init() {
    if (initialized) return;
    var mceContainer = document.querySelector('.mce-container');
    if (!mceContainer) return;

    initialized = true;
    injectStyles();
    createTriggerButton(mceContainer);
    createFloatingUI();
    setupTypewriterMode();
    setupRegisterIntercept();
  }

  // ---- 登録ボタン インターセプト ----------------------------------------

  function hasTag() {
    if (typeof tinymce !== 'undefined') {
      var editor = tinymce.get('inc_editor') || tinymce.activeEditor;
      if (editor) {
        var content = editor.getContent({ format: 'text' });
        return content.indexOf('【業務区分】') !== -1;
      }
    }
    var ta = document.querySelector('textarea#inc_editor')
      || document.querySelector('textarea[name="schedule.workText"]');
    if (ta) return ta.value.indexOf('【業務区分】') !== -1;
    return true;
  }

  var bypassIntercept = false;

  function setupRegisterIntercept() {
    function findAndAttach() {
      var candidates = document.querySelectorAll(
        'button, input[type="submit"], input[type="button"]'
      );
      for (var i = 0; i < candidates.length; i++) {
        var el = candidates[i];
        if (el._mkhIntercepted) continue;
        var text = (el.textContent || el.value || '').trim();
        if (text === '登録') {
          el._mkhIntercepted = true;
          (function(btn) {
            btn.addEventListener('click', function(e) {
              if (bypassIntercept) return;
              if (!hasTag()) {
                e.preventDefault();
                e.stopImmediatePropagation();
                showTagWarning(btn);
              }
            }, true);
          })(el);
        }
      }
    }
    findAndAttach();
    var obs = new MutationObserver(findAndAttach);
    obs.observe(document.body, { childList: true, subtree: true });
  }

  function showTagWarning(originalBtn) {
    var overlay = document.createElement('div');
    overlay.id = 'mkh-warning-overlay';
    overlay.innerHTML = [
      '<div id="mkh-warning-dialog">',
      '  <div id="mkh-warning-title">⚠️ タグが入力されていません</div>',
      '  <div id="mkh-warning-body">日報補助ボタンから業務区分・ステータスを入力すると、後から集計・AI分析に活用できます。</div>',
      '  <div id="mkh-warning-buttons">',
      '    <button type="button" id="mkh-warn-open">タグを入力する</button>',
      '    <button type="button" id="mkh-warn-skip">このまま登録する</button>',
      '  </div>',
      '</div>'
    ].join('');
    document.body.appendChild(overlay);

    document.getElementById('mkh-warn-open').addEventListener('click', function() {
      document.body.removeChild(overlay);
      showUI();
    });

    document.getElementById('mkh-warn-skip').addEventListener('click', function() {
      document.body.removeChild(overlay);
      bypassIntercept = true;
      originalBtn.click();
      bypassIntercept = false;
    });
  }

  // -----------------------------------------------------------------------

  function setupTypewriterMode() {
    var editor = (typeof tinymce !== 'undefined') && (tinymce.get('inc_editor') || tinymce.activeEditor);
    if (!editor) {
      setTimeout(setupTypewriterMode, 500);
      return;
    }
    editor.on('keyup NodeChange', function() {
      var doc = editor.getDoc();
      var sel = doc.getSelection();
      if (!sel || !sel.rangeCount) return;
      var range = sel.getRangeAt(0);
      var rect = range.getBoundingClientRect();
      if (!rect || (rect.top === 0 && rect.bottom === 0)) return;
      var win = editor.getWin();
      var body = editor.getBody();
      var halfHeight = win.innerHeight / 2;
      var currentScrollY = win.scrollY || win.pageYOffset || 0;
      var newScrollY = currentScrollY + rect.top - halfHeight;
      var maxScrollY = Math.max(0, body.scrollHeight - win.innerHeight);
      win.scrollTo(0, Math.max(0, Math.min(newScrollY, maxScrollY)));
    });
  }

  function createTriggerButton(mceContainer) {
    triggerBtn = document.createElement('button');
    triggerBtn.id = 'mkh-trigger';
    triggerBtn.type = 'button';
    triggerBtn.textContent = '日報補助';
    triggerBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      e.preventDefault();
      if (isUIVisible) {
        hideUI();
      } else {
        showUI();
      }
    });

    // mceContainerの親をrelativeにして右上に絶対配置
    var parent = mceContainer.parentElement;
    if (parent.style.position !== 'relative' && parent.style.position !== 'absolute') {
      parent.style.position = 'relative';
    }
    triggerBtn.style.position = 'absolute';
    triggerBtn.style.top = '2px';
    triggerBtn.style.right = '2px';
    triggerBtn.style.zIndex = '999998';
    parent.appendChild(triggerBtn);
  }

  function createFloatingUI() {
    floatingUI = document.createElement('div');
    floatingUI.id = 'mykomon-helper';

    var html = '<div id="mkh-header">MyKomon 日報入力補助</div>';

    html += '<div class="mkh-card">';
    html += '<div class="mkh-card-title">[1] 業務区分</div>';
    html += '<div class="mkh-options" id="mkh-category">';
    html += '<button type="button" class="mkh-btn" data-value="申告">申告</button>';
    html += '<button type="button" class="mkh-btn" data-value="相談">相談</button>';
    html += '<button type="button" class="mkh-btn" data-value="監査">監査</button>';
    html += '<button type="button" class="mkh-btn" data-value="記帳代行">記帳代行</button>';
    html += '<button type="button" class="mkh-btn" data-value="その他">その他</button>';
    html += '</div></div>';

    html += '<div class="mkh-card">';
    html += '<div class="mkh-card-title">[2] 業務ステータス</div>';
    html += '<div class="mkh-options" id="mkh-status">';
    html += '<button type="button" class="mkh-btn" data-value="完了">完了</button>';
    html += '<button type="button" class="mkh-btn" data-value="継続">継続</button>';
    html += '<button type="button" class="mkh-btn" data-value="中断">中断</button>';
    html += '</div></div>';

    html += '<div class="mkh-card" id="mkh-process-card" style="display:none">';
    html += '<div class="mkh-card-title">[3] 工程（今どの段階か）</div>';
    html += '<div class="mkh-options" id="mkh-process">';
    html += '<button type="button" class="mkh-btn" data-value="資料回収中">資料回収中</button>';
    html += '<button type="button" class="mkh-btn" data-value="作業中">作業中</button>';
    html += '<button type="button" class="mkh-btn" data-value="チェック中">チェック中</button>';
    html += '<button type="button" class="mkh-btn" data-value="顧客確認待ち">顧客確認待ち</button>';
    html += '<button type="button" class="mkh-btn" data-value="提出済み">提出済み</button>';
    html += '</div></div>';

    html += '<div class="mkh-card" id="mkh-blocking-card" style="display:none">';
    html += '<div class="mkh-card-title">[4] 阻害要因（複数選択可）</div>';
    html += '<div class="mkh-options" id="mkh-blocking">';
    html += '<button type="button" class="mkh-btn" data-value="資料未回収（顧客）">資料未回収（顧客）</button>';
    html += '<button type="button" class="mkh-btn" data-value="資料不備・不整合">資料不備・不整合</button>';
    html += '<button type="button" class="mkh-btn" data-value="顧客回答待ち">顧客回答待ち</button>';
    html += '<button type="button" class="mkh-btn" data-value="社内レビュー待ち">社内レビュー待ち</button>';
    html += '<button type="button" class="mkh-btn" data-value="差戻し・手戻り">差戻し・手戻り</button>';
    html += '<button type="button" class="mkh-btn" data-value="知識・判断不足">知識・判断不足</button>';
    html += '<button type="button" class="mkh-btn" data-value="外部先待ち">外部先待ち</button>';
    html += '<button type="button" class="mkh-btn" data-value="その他">その他</button>';
    html += '</div></div>';

    html += '<div class="mkh-card" id="mkh-urgency-card" style="display:none">';
    html += '<div class="mkh-card-title">[5] 緊急度</div>';
    html += '<div class="mkh-options" id="mkh-urgency">';
    html += '<button type="button" class="mkh-btn" data-value="通常">通常</button>';
    html += '<button type="button" class="mkh-btn mkh-btn-yellow" data-value="Yellow">Yellow</button>';
    html += '<button type="button" class="mkh-btn mkh-btn-red" data-value="Red">Red</button>';
    html += '</div></div>';

    html += '<div class="mkh-card">';
    html += '<div class="mkh-card-title">[6] 工数（任意）</div>';
    html += '<div class="mkh-options" id="mkh-workload">';
    html += '<button type="button" class="mkh-btn" data-value="〜30分">〜30分</button>';
    html += '<button type="button" class="mkh-btn" data-value="〜1時間">〜1時間</button>';
    html += '<button type="button" class="mkh-btn" data-value="〜2時間">〜2時間</button>';
    html += '<button type="button" class="mkh-btn" data-value="〜3時間">〜3時間</button>';
    html += '<button type="button" class="mkh-btn" data-value="3時間超">3時間超</button>';
    html += '</div></div>';

    html += '<div id="mkh-message"></div>';
    html += '<div id="mkh-success"></div>';
    html += '<button type="button" id="mkh-insert-btn">平文に反映する</button>';

    floatingUI.innerHTML = html;
    floatingUI.style.display = 'none';
    document.body.appendChild(floatingUI);
    setupCardEvents();
  }

  function showUI() {
    resetState();
    floatingUI.style.display = 'block';
    isUIVisible = true;
    triggerBtn.classList.add('mkh-active');
  }

  function hideUI() {
    floatingUI.style.display = 'none';
    isUIVisible = false;
    triggerBtn.classList.remove('mkh-active');
  }

  function resetState() {
    state.category = null;
    state.status = null;
    state.process = null;
    state.blocking = [];
    state.urgency = null;
    state.workload = null;
    var btns = floatingUI.querySelectorAll('.mkh-btn');
    for (var i = 0; i < btns.length; i++) btns[i].classList.remove('mkh-selected');
    document.getElementById('mkh-process-card').style.display = 'none';
    document.getElementById('mkh-blocking-card').style.display = 'none';
    document.getElementById('mkh-urgency-card').style.display = 'none';
    document.getElementById('mkh-message').textContent = '';
    document.getElementById('mkh-success').textContent = '';
  }

  function setupCardEvents() {
    document.getElementById('mkh-category').addEventListener('click', function(e) {
      var btn = e.target.closest('.mkh-btn');
      if (!btn) return;
      toggleSingle('mkh-category', 'category', btn);
      clearMessage();
    });

    document.getElementById('mkh-status').addEventListener('click', function(e) {
      var btn = e.target.closest('.mkh-btn');
      if (!btn) return;
      toggleSingle('mkh-status', 'status', btn);
      updateBlockingVisibility();
      clearMessage();
    });

    document.getElementById('mkh-process').addEventListener('click', function(e) {
      var btn = e.target.closest('.mkh-btn');
      if (!btn) return;
      toggleSingle('mkh-process', 'process', btn);
      clearMessage();
    });

    document.getElementById('mkh-blocking').addEventListener('click', function(e) {
      var btn = e.target.closest('.mkh-btn');
      if (!btn) return;
      toggleMulti(btn);
      clearMessage();
    });

    document.getElementById('mkh-urgency').addEventListener('click', function(e) {
      var btn = e.target.closest('.mkh-btn');
      if (!btn) return;
      toggleSingle('mkh-urgency', 'urgency', btn);
      clearMessage();
    });

    document.getElementById('mkh-workload').addEventListener('click', function(e) {
      var btn = e.target.closest('.mkh-btn');
      if (!btn) return;
      toggleSingle('mkh-workload', 'workload', btn);
      clearMessage();
    });

    document.getElementById('mkh-insert-btn').addEventListener('click', function() {
      if (!state.category) { showMessage('業務区分を選択してください'); return; }
      if (!state.status) { showMessage('業務ステータスを選択してください'); return; }
      var tag = buildTag();
      var ok = insertTag(tag);
      if (ok) {
        document.getElementById('mkh-success').textContent = '反映しました';
        setTimeout(hideUI, 800);
      } else {
        showMessage('挿入に失敗しました。ページを再読み込みしてください。');
      }
    });
  }

  function toggleSingle(containerId, stateKey, btn) {
    var container = document.getElementById(containerId);
    if (state[stateKey] === btn.dataset.value) {
      state[stateKey] = null;
      btn.classList.remove('mkh-selected');
    } else {
      var btns = container.querySelectorAll('.mkh-btn');
      for (var i = 0; i < btns.length; i++) btns[i].classList.remove('mkh-selected');
      state[stateKey] = btn.dataset.value;
      btn.classList.add('mkh-selected');
    }
  }

  function toggleMulti(btn) {
    var value = btn.dataset.value;
    var index = state.blocking.indexOf(value);
    if (index === -1) {
      state.blocking.push(value);
      btn.classList.add('mkh-selected');
    } else {
      state.blocking.splice(index, 1);
      btn.classList.remove('mkh-selected');
    }
  }

  function updateBlockingVisibility() {
    var show = state.status === '継続' || state.status === '中断';
    document.getElementById('mkh-process-card').style.display = show ? 'block' : 'none';
    document.getElementById('mkh-blocking-card').style.display = show ? 'block' : 'none';
    document.getElementById('mkh-urgency-card').style.display = show ? 'block' : 'none';
    if (!show) {
      state.process = null;
      var processBtns = document.querySelectorAll('#mkh-process .mkh-btn');
      for (var i = 0; i < processBtns.length; i++) processBtns[i].classList.remove('mkh-selected');
      state.blocking = [];
      var blockingBtns = document.querySelectorAll('#mkh-blocking .mkh-btn');
      for (var j = 0; j < blockingBtns.length; j++) blockingBtns[j].classList.remove('mkh-selected');
      state.urgency = null;
      var urgencyBtns = document.querySelectorAll('#mkh-urgency .mkh-btn');
      for (var k = 0; k < urgencyBtns.length; k++) urgencyBtns[k].classList.remove('mkh-selected');
    }
  }

  function buildTag() {
    var blockingText = state.blocking.length > 0 ? state.blocking.join('・') : null;
    var blockingHashtags = state.blocking.map(function(v) { return '#阻害要因_' + v; }).join(' ');
    var tag = '\n---\n';
    tag += '【業務区分】' + state.category + '\n';
    tag += '【ステータス】' + state.status + '\n';
    if (state.process) tag += '【工程】' + state.process + '\n';
    if (blockingText) tag += '【阻害要因】' + blockingText + '\n';
    if (state.urgency) tag += '【緊急度】' + state.urgency + '\n';
    if (state.workload) tag += '【工数】' + state.workload + '\n';
    tag += '#業務区分_' + state.category + ' #ステータス_' + state.status;
    if (state.process) tag += ' #工程_' + state.process;
    if (blockingHashtags) tag += ' ' + blockingHashtags;
    if (state.urgency) tag += ' #緊急度_' + state.urgency;
    if (state.workload) tag += ' #工数_' + state.workload;
    return tag;
  }

  function insertTag(tag) {
    var htmlTag = tag.replace(/\n/g, '<br>');
    if (typeof tinymce !== 'undefined') {
      var editor = tinymce.get('inc_editor') || tinymce.activeEditor;
      if (editor) {
        editor.execCommand('mceInsertContent', false, htmlTag);
        return true;
      }
    }
    var ta = document.querySelector('textarea#inc_editor')
      || document.querySelector('textarea[name="schedule.workText"]');
    if (ta) {
      ta.value += tag;
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      return true;
    }
    return false;
  }

  function showMessage(msg) {
    document.getElementById('mkh-message').textContent = msg;
  }

  function clearMessage() {
    document.getElementById('mkh-message').textContent = '';
    document.getElementById('mkh-success').textContent = '';
  }

  document.addEventListener('click', function(e) {
    if (!isUIVisible) return;
    if (floatingUI && floatingUI.contains(e.target)) return;
    if (triggerBtn && triggerBtn.contains(e.target)) return;
    hideUI();
  });

  function injectStyles() {
    var style = document.createElement('style');
    style.textContent = [
      '#mkh-trigger {',
      '  padding: 5px 14px;',
      '  background: #1a56a0; color: white;',
      '  border: none; border-radius: 4px;',
      '  font-size: 12px; cursor: pointer;',
      '  font-family: Meiryo, sans-serif; display: inline-block;',
      '}',
      '#mkh-trigger:hover, #mkh-trigger.mkh-active { background: #154a8a; }',
      '#mykomon-helper {',
      '  position: fixed; top: 10px; right: 10px; z-index: 999999;',
      '  background: #f5f7fa; border: 1px solid #c0cfe0;',
      '  border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.18);',
      '  width: 340px; font-family: Meiryo, sans-serif;',
      '  font-size: 13px; color: #333;',
      '  max-height: calc(100vh - 20px); overflow-y: auto;',
      '}',
      '#mkh-header {',
      '  background: #1a56a0; color: white;',
      '  padding: 10px 14px; font-size: 13px; font-weight: bold;',
      '  border-radius: 8px 8px 0 0;',
      '}',
      '#mykomon-helper .mkh-card {',
      '  background: white; margin: 10px;',
      '  border-radius: 6px; padding: 12px;',
      '  box-shadow: 0 1px 3px rgba(0,0,0,0.08);',
      '}',
      '#mykomon-helper .mkh-card-title {',
      '  font-weight: bold; margin-bottom: 8px;',
      '  color: #1a56a0; font-size: 11px;',
      '}',
      '#mykomon-helper .mkh-options { display: flex; flex-wrap: wrap; gap: 6px; }',
      '#mykomon-helper .mkh-btn {',
      '  padding: 5px 11px; border: 1.5px solid #ccc;',
      '  border-radius: 20px; background: white; cursor: pointer;',
      '  font-size: 12px; font-family: Meiryo, sans-serif;',
      '}',
      '#mykomon-helper .mkh-btn:hover { border-color: #1a56a0; color: #1a56a0; }',
      '#mykomon-helper .mkh-btn.mkh-selected {',
      '  background: #1a56a0; border-color: #1a56a0; color: white;',
      '}',
      '#mykomon-helper .mkh-btn-yellow { border-color: #e6a817; color: #a06800; }',
      '#mykomon-helper .mkh-btn-yellow:hover, #mykomon-helper .mkh-btn-yellow.mkh-selected { background: #e6a817; border-color: #e6a817; color: white; }',
      '#mykomon-helper .mkh-btn-red { border-color: #c0392b; color: #c0392b; }',
      '#mykomon-helper .mkh-btn-red:hover, #mykomon-helper .mkh-btn-red.mkh-selected { background: #c0392b; border-color: #c0392b; color: white; }',
      '#mkh-message { text-align: center; font-size: 11px; color: #e74c3c; margin: -4px 10px 4px; min-height: 14px; }',
      '#mkh-success { text-align: center; font-size: 11px; color: #27ae60; margin: -4px 10px 4px; min-height: 14px; }',
      '#mkh-insert-btn {',
      '  display: block; width: calc(100% - 20px);',
      '  margin: 0 10px 12px; padding: 10px;',
      '  background: #1a56a0; color: white; border: none;',
      '  border-radius: 6px; font-size: 13px; font-weight: bold;',
      '  cursor: pointer; font-family: Meiryo, sans-serif;',
      '}',
      '#mkh-insert-btn:hover { background: #154a8a; }',
      '#mkh-warning-overlay {',
      '  position: fixed; top: 0; left: 0; width: 100%; height: 100%;',
      '  background: rgba(0,0,0,0.55); z-index: 9999999;',
      '  display: flex; align-items: center; justify-content: center;',
      '}',
      '#mkh-warning-dialog {',
      '  background: white; border-radius: 10px; padding: 28px 28px 20px;',
      '  box-shadow: 0 8px 32px rgba(0,0,0,0.28); max-width: 360px; width: 90%;',
      '  font-family: Meiryo, sans-serif;',
      '}',
      '#mkh-warning-title {',
      '  font-size: 15px; font-weight: bold; color: #c0392b; margin-bottom: 12px;',
      '}',
      '#mkh-warning-body {',
      '  font-size: 13px; color: #333; line-height: 1.6; margin-bottom: 20px;',
      '}',
      '#mkh-warning-buttons { display: flex; gap: 10px; }',
      '#mkh-warn-open {',
      '  flex: 1; padding: 10px; background: #1a56a0; color: white;',
      '  border: none; border-radius: 6px; font-size: 13px; font-weight: bold;',
      '  cursor: pointer; font-family: Meiryo, sans-serif;',
      '}',
      '#mkh-warn-open:hover { background: #154a8a; }',
      '#mkh-warn-skip {',
      '  flex: 1; padding: 10px; background: white; color: #777;',
      '  border: 1.5px solid #ccc; border-radius: 6px; font-size: 12px;',
      '  cursor: pointer; font-family: Meiryo, sans-serif;',
      '}',
      '#mkh-warn-skip:hover { background: #f5f5f5; color: #555; }'
    ].join('\n');
    document.head.appendChild(style);
  }

  var checkCount = 0;
  var waitInterval = setInterval(function() {
    checkCount++;
    if (initialized || checkCount > 40) {
      clearInterval(waitInterval);
      return;
    }
    init();
  }, 500);

})();
