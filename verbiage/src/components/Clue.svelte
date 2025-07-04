<script>
  import { onMount, onDestroy } from "svelte";
  import Typed from "typed.js";

  // Props using Svelte 5 runes
  let { text, guess } = $props();

  let formattedText = $derived(
    text
      .replace(guess, `<span class="guess">${guess}</span>`)
      .replace("THE WORD", "<span class='the-word'>THE WORD</span>")
  );

  let typedElement;
  let typed;

  onMount(() => {
    if (typedElement && text) {
      typed = new Typed(typedElement, {
        strings: [text],
        typeSpeed: 200,
        showCursor: true,
        onComplete: () => {
          // Optional: callback when typing is complete
        },
      });
    }
  });

  onDestroy(() => {
    if (typed) {
      typed.destroy();
    }
  });

  // Watch for text changes and reinitialize typed.js
  $effect(() => {
    if (typed && text) {
      typed.destroy();
      typed = new Typed(typedElement, {
        strings: [formattedText],
        typeSpeed: 20,
        showCursor: true,
        startDelay: 600,
        onComplete: () => {
          typed.cursor.style.display = "none";
          // Optional: callback when typing is complete
        },
      });
    }
  });
</script>

<div class="clue-container">
  <!-- Background div with full text at 0 opacity to reserve space -->
  <div class="clue-background" aria-hidden="true">
    {@html formattedText}
  </div>

  <!-- Typewriter effect overlay -->
  <p class="clue">
    <span bind:this={typedElement}></span>
  </p>
</div>

<style>
  .clue-container {
    position: relative;
    margin-top: 1rem;
    margin-bottom: 1rem;
  }

  .clue-background {
    opacity: 0;
    text-align: left;
    line-height: 1.5;
    pointer-events: none;
  }

  .clue {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    text-align: left;
    margin: 0;
    line-height: 1.5;
  }

  :global(.clue .the-word),
  :global(.clue-background .the-word) {
    color: #000000;
    font-weight: 600;
  }

  :global(.clue .guess),
  :global(.clue-background .guess) {
    color: #000000;
    font-weight: 600;
  }
</style>
