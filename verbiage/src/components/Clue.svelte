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
        onComplete: () => {
          typed.cursor.style.display = "none";
          // Optional: callback when typing is complete
        },
      });
    }
  });
</script>

<p class="clue">
  <span bind:this={typedElement}></span>
</p>

<style>
  .clue {
    text-align: left;
    margin-bottom: 1rem;
    line-height: 1.5;
  }
  :global(.clue .the-word) {
    color: #000000;
    font-weight: 600;
  }
  :global(.clue .guess) {
    color: #000000;
    font-weight: 600;
  }
</style>
