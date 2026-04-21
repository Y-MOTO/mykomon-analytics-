// 選択状態を管理
const state = {
  category: null,    // 業務区分（単一選択）
  status: null,      // ステータス（単一選択）
  blocking: [],      // 阻害要因（複数選択）
};

// 単一選択の処理
function setupSingleSelect(containerId, stateKey) {
  const container = document.getElementById(containerId);
  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.option-btn');
    if (!btn) return;

    // 同じボタンをクリックしたら選択解除
    if (state[stateKey] === btn.dataset.value) {
      state[stateKey] = null;
      btn.classList.remove('selected');
    } else {
      // 他のボタンの選択を解除
      container.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
      state[stateKey] = btn.dataset.value;
      btn.classList.add('selected');
    }

    // ステータス変更時は阻害要因カードの表示/非表示を切り替え
    if (stateKey === 'status') {
      updateBlockingVisibility();
    }

    clearMessages();
  });
}

// 複数選択の処理
function setupMultiSelect(containerId, stateKey) {
  const container = document.getElementById(containerId);
  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.option-btn');
    if (!btn) return;

    const value = btn.dataset.value;
    const index = state[stateKey].indexOf(value);

    if (index === -1) {
      state[stateKey].push(value);
      btn.classList.add('selected');
    } else {
      state[stateKey].splice(index, 1);
      btn.classList.remove('selected');
    }

    clearMessages();
  });
}

// 阻害要因カードの表示制御
function updateBlockingVisibility() {
  const card = document.getElementById('card-blocking');
  const isVisible = state.status === '継続' || state.status === '中断';

  card.style.display = isVisible ? 'block' : 'none';

  // 非表示にした場合は選択をリセット
  if (!isVisible) {
    state.blocking = [];
    document.querySelectorAll('#options-blocking .option-btn').forEach(b => {
      b.classList.remove('selected');
    });
  }
}

// 構造化タグを生成
function buildTag() {
  const blockingText = state.blocking.length > 0
    ? state.blocking.join('・')
    : null;

  const blockingHashtags = state.blocking.length > 0
    ? state.blocking.map(v => `#阻害要因_${v}`).join(' ')
    : '';

  let tag = '\n---\n';
  tag += `【業務区分】${state.category}\n`;
  tag += `【ステータス】${state.status}\n`;

  if (blockingText) {
    tag += `【阻害要因】${blockingText}\n`;
  }

  tag += `#業務区分_${state.category} #ステータス_${state.status}`;
  if (blockingHashtags) {
    tag += ` ${blockingHashtags}`;
  }

  return tag;
}

// メッセージをクリア
function clearMessages() {
  document.getElementById('message').textContent = '';
  document.getElementById('success-msg').textContent = '';
}

// 「平文に反映する」ボタン
document.getElementById('insert-btn').addEventListener('click', async () => {
  clearMessages();

  // バリデーション
  if (!state.category) {
    document.getElementById('message').textContent = '業務区分を選択してください';
    return;
  }
  if (!state.status) {
    document.getElementById('message').textContent = '業務ステータスを選択してください';
    return;
  }

  const tag = buildTag();

  // content.js にメッセージを送信してテキストエリアに挿入
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const result = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: insertTagToTextarea,
      args: [tag],
      world: "MAIN",
    });

    if (result[0].result === true) {
      document.getElementById('success-msg').textContent = '✓ 日報入力欄に反映しました';
    } else {
      document.getElementById('message').textContent = '日報入力欄が見つかりませんでした。日報入力画面を開いてください。';
    }
  } catch (e) {
    document.getElementById('message').textContent = 'エラーが発生しました。ページを再読み込みしてください。';
    console.error(e);
  }
});

// テキストエリアへの挿入処理（content scriptとして実行される関数）
function insertTagToTextarea(tag) {
  // TinyMCEエディタが存在する場合はそちらを優先
  if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
    tinymce.activeEditor.execCommand('mceInsertContent', false, tag.replace(/\n/g, '<br>'));
    return true;
  }

  // TinyMCEをIDで取得
  if (typeof tinymce !== 'undefined') {
    const editor = tinymce.get('inc_editor');
    if (editor) {
      editor.execCommand('mceInsertContent', false, tag.replace(/\n/g, '<br>'));
      return true;
    }
  }

  const textarea = document.querySelector('textarea#inc_editor')
    || document.querySelector('textarea[name="schedule.workText"]')
    || document.querySelector('textarea.richtextarea');

  if (!textarea) return false;

  textarea.focus();
  textarea.value = textarea.value + tag;

  const inputEvent = new Event('input', { bubbles: true });
  textarea.dispatchEvent(inputEvent);
  const changeEvent = new Event('change', { bubbles: true });
  textarea.dispatchEvent(changeEvent);

  textarea.selectionStart = textarea.selectionEnd = textarea.value.length;

  return true;
}

// 初期化
setupSingleSelect('options-category', 'category');
setupSingleSelect('options-status', 'status');
setupMultiSelect('options-blocking', 'blocking');
