<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import PWAInstallButton from "./PWAInstallButton.svelte";

  let { onShareGame, guessCount, elapsedTime = "" } = $props();

  // Helper function for pluralization based on language
  let plural = $derived(
    $locale === "fr"
      ? guessCount === 1
        ? ""
        : "s" // French: tentative/tentatives
      : guessCount === 1
        ? ""
        : "es" // English: guess/guesses
  );
</script>

<div class="victory">
  <div class="celebration-icon">🎉</div>
  <h2>{$_("wellDone")}</h2>
  <p>
    {$_("solvedInTimeAndGuesses", {
      values: { time: elapsedTime, count: guessCount, plural },
    })}
  </p>
  <div class="victory-actions">
    <button onclick={onShareGame} class="action-btn">
      {$_("shareGameAction")}
    </button>
    <p class="github-link">
      <a
        href="https://github.com/Zulko/verbiage"
        target="_blank"
        rel="noopener noreferrer"
      >
        {$_("visitGithub")}
        <img src="/github-icon.svg" alt="GitHub" class="github-icon" />
      </a>
    </p>
    <PWAInstallButton />
  </div>
</div>

<style>
  .victory {
    text-align: center;
    padding: 0 1.5rem;
    margin-top: 1rem;
    font-family: system-ui, Avenir, Helvetica, Arial, sans-serif;
  }

  .celebration-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    animation: gentle-bounce 2s ease-in-out infinite;
  }

  .victory h2 {
    color: #000000;
    margin-bottom: 0.5rem;
    font-size: 1.8rem;
    font-weight: 500;
  }

  .victory p {
    margin-bottom: 1.5rem;
    font-size: 1rem;
    color: #000000;
    font-weight: 400;
  }

  .victory-actions {
    display: flex;
    gap: 0.75rem;
    flex-direction: column;
  }

  .action-btn {
    border-radius: 8px;
    border: 1px solid #000000;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    font-weight: 500;
    font-family: inherit;
    cursor: pointer;
    transition:
      border-color 0.25s,
      background-color 0.25s;
    width: 100%;
    background-color: #ffffff;
    color: #000000;
  }

  .action-btn:hover {
    background-color: #000000;
    color: #ffffff;
  }

  .github-link {
    margin-top: 1rem;
    margin-bottom: 0;
    font-size: 0.875rem;
    opacity: 0.7;
  }

  .github-link a {
    color: #000000;
    text-decoration: underline;
    text-decoration-color: rgba(0, 0, 0, 0.3);
    transition: all 0.25s ease;
    font-weight: 400;
  }

  .github-link a:hover {
    color: #000000;
    text-decoration-color: #000000;
    opacity: 1;
  }

  .github-icon {
    height: 1rem;
    width: auto;
    margin-left: 0.25rem;
  }

  @keyframes gentle-bounce {
    0%,
    20%,
    50%,
    80%,
    100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-3px);
    }
    60% {
      transform: translateY(-1px);
    }
  }

  /* Responsive adjustments */
  @media (max-width: 480px) {
    .victory {
      padding: 1.5rem 1rem;
    }

    .celebration-icon {
      font-size: 2.5rem;
    }

    .victory h2 {
      font-size: 1.6rem;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .victory h2 {
      color: #ffffff;
    }

    .victory p {
      color: #ffffff;
    }

    .action-btn {
      background-color: #ffffff;
      color: #000000;
      border: 1px solid #ffffff;
    }

    .action-btn:hover {
      background-color: #000000;
      color: #ffffff;
      border-color: #ffffff;
    }

    .github-link a {
      color: #ffffff;
      text-decoration-color: rgba(255, 255, 255, 0.3);
    }

    .github-link a:hover {
      color: #ffffff;
      text-decoration-color: #ffffff;
      opacity: 1;
    }

    .github-icon {
      filter: brightness(0) invert(1);
    }
  }
</style>
