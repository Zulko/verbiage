<script>
  import { locale, isLoading } from "svelte-i18n";
  const { switchLanguage } = $props();
</script>

{#if !$isLoading}
  <div class="language-flags">
    <button
      class="flag-btn {$locale.startsWith('en') ? 'active' : ''}"
      onclick={() => switchLanguage("en")}
      title="English"
    >
      🇺🇸
    </button>
    <button
      class="flag-btn {$locale === 'fr' ? 'active' : ''}"
      onclick={() => switchLanguage("fr")}
      title="Français"
    >
      🇫🇷
    </button>
  </div>
{/if}

<style>
  .language-flags {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    display: flex;
    gap: 0.25rem;
    z-index: 100;
  }

  .flag-btn {
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 0.25rem;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s ease;
    backdrop-filter: blur(5px);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    opacity: 0.6;
  }

  .flag-btn:hover {
    opacity: 0.9;
    background: rgba(255, 255, 255, 0.8);
  }

  .flag-btn.active {
    opacity: 1;
    border-color: rgba(52, 152, 219, 0.4);
    background: rgba(255, 255, 255, 0.9);
  }

  /* Responsive design */
  @media (max-width: 480px) {
    .language-flags {
      top: 0.5rem;
      right: 0.5rem;
    }

    .flag-btn {
      width: 28px;
      height: 28px;
      font-size: 0.8rem;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .flag-btn {
      background: rgba(30, 30, 30, 0.7);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    .flag-btn:hover {
      opacity: 0.9;
      background: rgba(30, 30, 30, 0.8);
    }
  }
</style>
