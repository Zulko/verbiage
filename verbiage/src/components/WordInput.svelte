<script>
  import { _ } from "svelte-i18n";

  let { currentWord, wordSize } = $props();
</script>

<div class="word-input">
  {#each Array(wordSize)
    .fill(0)
    .map((_, i) => i) as index}
    <div class="letter" class:empty={!currentWord[index]}>
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
    margin: 0.5rem 0;
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
</style>
