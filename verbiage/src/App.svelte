<script>
  import { onMount } from "svelte";
  import { _, locale, locales, isLoading } from "svelte-i18n";
  import { fly } from "svelte/transition";
  import autoAnimate from "@formkit/auto-animate";
  import "./lib/i18n.js";
  import VictorySection from "./components/VictorySection.svelte";
  import LanguageFlags from "./components/LanguageFlags.svelte";
  import Keyboard from "./components/Keyboard.svelte";
  import Clue from "./components/Clue.svelte";
  import WordInput from "./components/WordInput.svelte";
  import PuzzleCalendar from "./components/PuzzleCalendar.svelte";
  import puzzleCalendars from "./lib/puzzleCalendars.json";

  // State to track when game is ending
  let gameEnding = $state(false);

  // State management using $state
  let settings = $state({
    date: null,
    lang: null,
  });

  let previousGuesses = $state([]);
  let currentWord = $state("");
  let puzzle = $state(null);
  let gameState = $state("playing");
  let tStart = $state(null);
  let tEnd = $state(null);
  let errorMessage = $state("");
  let showCalendar = $state(false);

  function formatDate(dateStr, lang) {
    const [year, month, day] = dateStr.split("-").map((n) => parseInt(n, 10));
    const date = new Date(year, month - 1, day);
    const locale = lang === "fr" ? "fr-FR" : "en-US";
    return new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(date);
  }

  let formattedDate = $derived(
    settings.date && settings.lang
      ? formatDate(settings.date, settings.lang)
      : ""
  );

  const puzzleCalendar = $derived(puzzleCalendars[settings.lang]);

  $effect(() => {
    if (settings.lang && settings.date) {
      loadPuzzle(settings);
      updateURL();
      tStart = Date.now();
      previousGuesses = [];
      gameState = "playing";
      gameEnding = false;
      currentWord = "";
    }
  });

  function switchLanguage(lang) {
    const langPuzzles = puzzleCalendars[lang];
    if (!langPuzzles || langPuzzles.length === 0) {
      console.warn(`No puzzles available for language: ${lang}`);
      return;
    }
    if (settings.date && langPuzzles.includes(settings.date)) {
      settings.lang = lang;
    } else {
      settings = { lang, date: langPuzzles[0] };
    }
    $locale = lang;
  }

  function toggleCalendar() {
    showCalendar = !showCalendar;
  }

  // Component lifecycle
  onMount(() => {
    console.log("Starting Verbiage...");
    const urlParams = new URLSearchParams(window.location.search);
    let lang = urlParams.get("lang") || "en";

    // Fallback to a language that has puzzles if the requested one doesn't
    if (!puzzleCalendars[lang] || puzzleCalendars[lang].length === 0) {
      lang =
        Object.keys(puzzleCalendars).find(
          (l) => puzzleCalendars[l].length > 0
        ) || "en";
    }

    const date = urlParams.get("date") || puzzleCalendars[lang][0];
    settings = { lang, date };

    // Set the initial locale for i18n
    $locale = lang;
  });

  // Derived timing values
  let elapsedTimeFormatted = $derived(() => {
    if (!tStart || !tEnd) return "";

    const elapsedMs = tEnd - tStart;
    const totalSeconds = Math.floor(elapsedMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    return `${minutes}m:${seconds.toString().padStart(2, "0")}s`;
  });

  async function loadPuzzle({ date, lang }) {
    const puzzleData = await fetch(`/puzzles/${lang}/${lang}_${date}.json.gz`);
    puzzle = await puzzleData.json();
  }

  function updateURL() {
    const params = new URLSearchParams();
    if (settings.date) {
      params.set("date", settings.date);
    }
    if (settings.lang) {
      params.set("lang", settings.lang);
    }
    const newURL = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, "", newURL);
  }
  // ===== Sharing/External =====
  function shareGame() {
    const gameURL = window.location.href;
    let title = $_("shareTitle");
    if (gameState === "won") {
      title = $_("shareWinTitleGuesses", {
        values: { time: elapsedTimeFormatted(), count: previousGuesses.length },
      });
    }
    // Check if Web Share API is supported and can share this data
    if (navigator.share && navigator.canShare) {
      const shareData = {
        title: title, // Not very compatible
        text: `${title}`, // Include title in text for iOS compatibility
        url: gameURL,
      };

      // Test if the data can be shared
      if (navigator.canShare(shareData)) {
        navigator.share(shareData).catch((error) => {
          // Fallback to clipboard on share error
          navigator.clipboard.writeText(`${title} ${gameURL}`);
          alert($_("urlCopied"));
        });
      } else {
        // Fallback: use text-only sharing which is more reliable on iOS
        navigator
          .share({
            text: `${title} ${gameURL}`,
          })
          .catch((error) => {
            navigator.clipboard.writeText(`${title} ${gameURL}`);
            alert($_("urlCopied"));
          });
      }
    } else {
      // Fallback for browsers without Web Share API
      navigator.clipboard.writeText(`${title} ${gameURL}`);
      alert($_("urlCopied"));
    }
  }

  function onKeyPress(key) {
    // Clear any previous error message
    errorMessage = "";

    if (key === "Enter") {
      // Only process Enter if word length matches solution length
      if (currentWord.length === puzzle.solution.length) {
        // Check if word was already submitted
        if (currentWord === puzzle.solution) {
          gameEnding = true;
          // Delay changing gameState to allow hinge animation to play
          setTimeout(() => {
            gameState = "won";
            gameEnding = false; // Remove the element from DOM after animation
            tEnd = Date.now();
          }, 500);
          return;
        } else if (previousGuesses.includes(currentWord)) {
          errorMessage = $_("alreadySubmitted", {
            values: { currentWord },
          });
        }
        // Check if the word exists in the puzzle
        else if (puzzle[currentWord]) {
          previousGuesses = [...previousGuesses, currentWord];
          currentWord = "";
        } else {
          errorMessage = $_("onlyCommonNouns", {
            values: { currentWord },
          });
        }
      }
    } else if (key === "Return") {
      // Backspace functionality
      if (currentWord.length > 0) {
        currentWord = currentWord.slice(0, -1);
      }
    } else {
      // Letter key pressed
      if (currentWord.length < puzzle.solution.length) {
        currentWord += key;
      }
    }
  }
</script>

<main>
  <LanguageFlags {switchLanguage} />

  {#if !$isLoading}
    <h1>Verbiage</h1>
    <button
      class="date"
      onclick={toggleCalendar}
      onkeydown={(e) =>
        e.key === "Enter" || e.key === " " ? toggleCalendar() : null}
      aria-label={$_("openCalendar") || "Open calendar"}
      type="button"
    >
      {$_("datePreposition")}
      {formattedDate}
      <img src="/calendar-icon.svg" alt="calendar" class="calendar-icon" />
    </button>

    <PuzzleCalendar
      bind:isOpen={showCalendar}
      enabledDates={puzzleCalendar}
      bind:date={settings.date}
      lang={settings.lang}
    />

    {#if puzzle}
      <section class="clues" use:autoAnimate>
        <Clue
          text={$_("firstClue", { values: { length: puzzle.solution.length } })}
        />
        {#each previousGuesses as guess}
          <div class="clue-separator"></div>
          <Clue text={puzzle[guess]} {guess} />
        {/each}
      </section>
    {/if}

    {#if (gameState === "playing" || gameEnding) && puzzle}
      <div
        class="game-container"
        class:animate__animated={gameEnding}
        class:animate__flipOutY={gameEnding}
      >
        <div
          class:animate__animated={errorMessage}
          class:animate__shakeX={errorMessage}
        >
          <WordInput {currentWord} wordSize={puzzle.solution.length} />
        </div>
        <div class="error-container">
          {#if errorMessage}
            <p class="error" in:fly={{ y: -10, duration: 150 }}>
              {errorMessage}
            </p>
          {/if}
        </div>
        <Keyboard
          lang={settings.lang}
          {onKeyPress}
          {currentWord}
          wordSize={puzzle.solution.length}
        />
      </div>
    {/if}

    {#if gameState === "won"}
      <div class="clue-separator"></div>
      <div class="solution-container animate__animated animate__zoomIn">
        <div class="solution"><b>THE WORD</b> is <b>{puzzle.solution}</b></div>
        <VictorySection
          onShareGame={shareGame}
          guessCount={previousGuesses.length}
          elapsedTime={elapsedTimeFormatted()}
        />
      </div>
    {/if}
  {:else}
    <!-- Loading state while i18n initializes -->
    <div class="loading">
      <h1>Verbiage</h1>
      <p>Loading...</p>
    </div>
  {/if}
</main>

<style>
  @import url("https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;800&display=swap");
  @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap");

  main {
    font-family:
      "Inter",
      system-ui,
      -apple-system,
      sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding: 2rem 0.2rem;
  }

  .clues {
    width: 100%;
    max-width: 380px;
    padding: 0 1rem;
  }

  .game-container {
    width: 100%;
    max-width: 600px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .error-container {
    height: 2rem;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 0.25rem;
    margin-bottom: 0.75rem;
  }

  .error {
    color: #e53e3e;
    margin: 0;
    text-align: center;
    font-size: 0.875rem;
  }

  h1 {
    margin: 0;
    font-family: "EB Garamond", serif;
    font-weight: 500;
    font-size: 4.5rem;
    letter-spacing: 0.05em;
    margin-bottom: -0.3rem;
  }

  .date {
    font-size: 0.8rem;
    color: #666;
    text-align: center;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s ease;
    background: none;
    border: none;
    font-family: inherit;
  }

  .date:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  .date:focus {
    outline: none;
    background-color: rgba(0, 0, 0, 0.1);
  }

  .date:focus-visible {
    outline: 2px solid #0087ff;
    outline-offset: 2px;
  }

  .calendar-icon {
    width: 1rem;
    height: 1rem;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .loading p {
    color: #666;
    margin-top: 0.5rem;
  }

  .solution {
    font-size: 1.5rem;
    margin: 1rem 0;
  }

  .clue-separator {
    width: 40px;
    height: 1px;
    background: #ccc;
    margin: 0.5rem auto;
  }

  .clue-separator::before {
    content: "";
  }
</style>
