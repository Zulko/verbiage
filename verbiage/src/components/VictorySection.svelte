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
    <button onclick={onNewGame} class="share-btn">
      {$_("newGameAction")}
    </button>
    <button onclick={onShareGame} class="new-game-btn">
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
    padding: 1.5rem 1.25rem;
    background: linear-gradient(135deg, #f0f9ff 0%, #dbeafe 50%, #fef3c7 100%);
    border: 1px solid #cbd5e1;
    border-radius: 1rem;
    margin-top: 2rem;
    box-shadow: 0 4px 16px rgba(52, 152, 219, 0.15);
  }

  .celebration-icon {
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
    animation: gentle-bounce 2s ease-in-out infinite;
  }

  .victory h2 {
    color: #1e293b;
    margin-bottom: 0.5rem;
    font-size: 1.6rem;
    font-weight: 600;
  }

  .victory p {
    margin-bottom: 1.25rem;
    font-size: 1.1rem;
    color: #475569;
    font-weight: 500;
  }

  .victory-actions {
    display: flex;
    gap: 0.5rem;
    flex-direction: column;
  }

  .share-btn {
    background: linear-gradient(135deg, #3498db 0%, #2563eb 100%);
    color: white;
    border: none;
    padding: 0.875rem 1.5rem;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
    box-shadow: 0 3px 8px rgba(52, 152, 219, 0.2);
  }

  .share-btn:hover {
    background: linear-gradient(135deg, #2980b9 0%, #1d4ed8 100%);
    transform: translateY(-1px);
    box-shadow: 0 5px 12px rgba(52, 152, 219, 0.3);
  }

  .new-game-btn {
    background: rgba(255, 255, 255, 0.9);
    color: #475569;
    border: 1px solid #e2e8f0;
    padding: 0.875rem 1.5rem;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
    backdrop-filter: blur(10px);
  }

  .new-game-btn:hover {
    background: rgba(255, 255, 255, 1);
    border-color: #3498db;
    color: #3498db;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  }

  .github-link {
    margin-top: 0.75rem;
    margin-bottom: 0;
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .github-link a {
    color: #64748b;
    text-decoration: underline;
    text-decoration-color: rgba(100, 116, 139, 0.4);
    transition: all 0.2s ease;
    font-weight: 400;
  }

  .github-link a:hover {
    color: #3498db;
    text-decoration-color: #3498db;
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
      padding: 1.25rem 1rem;
    }

    .celebration-icon {
      font-size: 2rem;
    }

    .victory h2 {
      font-size: 1.5rem;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .victory {
      background: linear-gradient(
        135deg,
        #1a365d 0%,
        #2d3748 50%,
        #744210 100%
      );
      border: 1px solid #4a5568;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }

    .victory h2 {
      color: #ffffff;
    }

    .victory p {
      color: #cbd5e0;
    }

    .new-game-btn {
      background: rgba(45, 55, 72, 0.9);
      color: #cbd5e0;
      border: 1px solid #4a5568;
      backdrop-filter: blur(10px);
    }

    .new-game-btn:hover {
      background: rgba(45, 55, 72, 1);
      border-color: #3498db;
      color: #3498db;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    }

    .github-link a {
      color: #a0aec0;
      text-decoration-color: rgba(160, 174, 192, 0.4);
    }

    .github-link a:hover {
      color: #3498db;
      text-decoration-color: #3498db;
    }

    .github-icon {
      filter: brightness(0) invert(1);
    }
  }
</style>
