<!--
    A keyboard component that allows the user to input a word.
    It displays the letters in a keyboard layout style on three rows:
    If lang=en: QWERTYUIOP/ASDFGHJKL/[Enter]ZXCVBNM[Return]
    If lang=fr: AZERTYUIOP/QSDFGHJKLM/[Enter]WXCVBN[Return]
    The user can click on a button to input the letter.
    The user can also press the keyboard keys to input the letter.
-->

<script>
  let { lang, onKeyPress, currentWord, wordSize } = $props();

  const wordLength = $derived(currentWord?.length ?? 0);

  const enLayout = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
    ["Enter", "Z", "X", "C", "V", "B", "N", "M", "Return"],
  ];

  const frLayout = [
    ["A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["Q", "S", "D", "F", "G", "H", "J", "K", "L", "M"],
    ["Enter", "W", "X", "C", "V", "B", "N", "Return"],
  ];

  $effect(() => {
    const handleKeyDown = (event) => {
      const key = event.key.toUpperCase();
      const layout = lang === "fr" ? frLayout : enLayout;
      const allKeys = layout.flat();

      // Handle letter keys
      if (allKeys.includes(key)) {
        event.preventDefault();
        onKeyPress(key);
        return;
      }

      // Handle special keys
      switch (key) {
        case "ENTER":
        case "RETURN":
          event.preventDefault();
          onKeyPress("Enter");
          break;
        case "BACKSPACE":
          event.preventDefault();
          onKeyPress("Return");
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  function isKeyDisabled(key) {
    if (key === "Return") {
      return wordLength === 0;
    }
    if (key === "Enter") {
      return wordLength < wordSize;
    }
    return wordLength === wordSize;
  }
</script>

<div class="keyboard">
  {#each lang === "fr" ? frLayout : enLayout as row}
    <div class="row">
      {#each row as key}
        <button
          class:special={key === "Enter" || key === "Return"}
          class:disabled={isKeyDisabled(key)}
          disabled={isKeyDisabled(key)}
          on:click={() => onKeyPress(key)}
        >
          {key === "Return" ? "⌫" : key}
        </button>
      {/each}
    </div>
  {/each}
</div>

<style>
  .keyboard {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.25rem;
    user-select: none;
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
    align-items: center;
  }

  .row {
    display: flex;
    justify-content: center;
    gap: 0.25rem;
    width: auto;
  }

  /* First row (10 keys) is 100% */
  .row:first-child {
    width: 100%;
  }

  /* Second row (9-10 keys) is ~90% */
  .row:nth-child(2) {
    width: 90%;
  }

  /* Third row (8-9 keys + wide special keys) is ~95% */
  .row:nth-child(3) {
    width: 95%;
  }

  button {
    flex: 1;
    min-width: 0;
    height: 3rem;
    padding: 0 0.25rem;
    border: none;
    border-radius: 0.25rem;
    background-color: #e2e8f0;
    color: #1a202c;
    font-weight: bold;
    font-size: clamp(1rem, 4vw, 1.25rem);
    cursor: pointer;
    transition: all 0.2s;
  }

  button:not(.disabled):hover {
    background-color: #cbd5e0;
  }

  button:not(.disabled):active {
    background-color: #a0aec0;
  }

  button.special {
    flex: 2.5;
    font-size: clamp(0.9rem, 3.5vw, 1.125rem);
    background-color: #cbd5e0;
  }

  button.special:not(.disabled):hover {
    background-color: #a0aec0;
  }

  button.special:not(.disabled):active {
    background-color: #718096;
  }

  button.disabled {
    background-color: #e2e8f0;
    opacity: 0.4;
    cursor: not-allowed;
  }

  @media (max-width: 360px) {
    .keyboard {
      padding: 0.125rem;
      gap: 0.125rem;
    }

    .row {
      gap: 0.125rem;
    }

    button {
      height: 2.75rem;
    }
  }
</style>
