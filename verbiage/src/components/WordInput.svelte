<script>
  import { _ } from "svelte-i18n";

  let { currentWord, wordSize } = $props();

  let previousLength = $state(0);
  let pulsedIndex = $state(-1);

  // Track when a new letter is added
  $effect(() => {
    if (currentWord.length > previousLength) {
      // A letter was added, pulse the new letter
      pulsedIndex = currentWord.length - 1;

      // Remove the pulse class after animation completes
      setTimeout(() => {
        pulsedIndex = -1;
      }, 200);
    }
    previousLength = currentWord.length;
  });
</script>

<div class="word-input">
  {#each Array(wordSize)
    .fill(0)
    .map((_, i) => i) as index}
    <div
      class="letter"
      class:empty={!currentWord[index]}
      class:pulse={index === pulsedIndex}
    >
      {currentWord[index]}
    </div>
  {/each}
</div>

<style>
  .word-input {
    display: flex;
    flex-direction: row;
    gap: 0.75rem;
    justify-content: center;
    margin: 2rem 0 0;
  }

  .letter {
    width: 3.5rem;
    height: 3.5rem;
    border: 2px solid #d3d6da;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    font-weight: bold;
    text-transform: uppercase;
    background: white;
    transition: all 0.2s ease;
  }

  .letter:not(.empty) {
    border-color: #878a8c;
  }

  .letter.pulse {
    animation: pulse 0.2s ease-out;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.05);
      box-shadow: 0 0 4px rgba(135, 138, 140, 0.3);
    }
    100% {
      transform: scale(1);
    }
  }

  @media (max-width: 600px) {
    .letter {
      width: 2.75rem;
      height: 2.75rem;
      font-size: 1.5rem;
    }
    .word-input {
      gap: 0.5rem;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .letter {
      background: #2d3748;
      color: #ffffff;
      border-color: #4a5568;
    }

    .letter:not(.empty) {
      border-color: #a0aec0;
    }

    .letter.pulse {
      box-shadow: 0 0 4px rgba(160, 174, 192, 0.3);
    }
  }
</style>
