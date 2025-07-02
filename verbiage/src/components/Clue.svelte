<script>
  import { onMount, onDestroy } from "svelte";
  import Typed from "typed.js";

  // Props using Svelte 5 runes
  let { text } = $props();

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
        strings: [text],
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
  @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap");

  .clue {
    text-align: left;
    margin-bottom: 1rem;
    font-family:
      "Inter",
      system-ui,
      -apple-system,
      sans-serif;
    font-weight: 400;
    line-height: 1.5;
  }
</style>
