<script>
  import { _ } from "svelte-i18n";
  import { onMount } from "svelte";

  let { currentDate = $bindable(), enabledDates = [], lang = "en" } = $props();

  let isOpen = $state(false);
  let dropdownRef = $state(null);

  function formatDateForDropdown(dateStr, lang) {
    const [year, month, day] = dateStr.split("-").map((n) => parseInt(n, 10));
    const date = new Date(year, month - 1, day);

    if (lang === "fr") {
      const dayNames = ["Dim.", "Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam."];
      const monthNames = [
        "Jan.",
        "Fév.",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juil.",
        "Août",
        "Sept.",
        "Oct.",
        "Nov.",
        "Déc.",
      ];
      const dayOfWeek = dayNames[date.getDay()];
      const monthName = monthNames[date.getMonth()];
      return `${dayOfWeek} ${day} ${monthName} ${year}`;
    } else {
      const dayNames = ["Sun.", "Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat."];
      const monthNames = [
        "Jan",
        "Feb",
        "March",
        "April",
        "May",
        "June",
        "July",
        "Aug",
        "Sept",
        "Oct",
        "Nov",
        "Dec",
      ];
      const dayOfWeek = dayNames[date.getDay()];
      const monthName = monthNames[date.getMonth()];
      return `${dayOfWeek} ${monthName} ${day}, ${year}`;
    }
  }

  function toggleDropdown() {
    isOpen = !isOpen;
  }

  function selectDate(date, event) {
    event.stopPropagation();
    currentDate = date;
    isOpen = false;
  }

  function handleClickOutside(event) {
    if (dropdownRef && !dropdownRef.contains(event.target)) {
      isOpen = false;
    }
  }

  function handleKeydown(event) {
    if (event.key === "Escape") {
      isOpen = false;
    }
  }

  function handleTriggerKeydown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleDropdown();
    }
  }

  onMount(() => {
    document.addEventListener("click", handleClickOutside);
    document.addEventListener("keydown", handleKeydown);

    return () => {
      document.removeEventListener("click", handleClickOutside);
      document.removeEventListener("keydown", handleKeydown);
    };
  });
</script>

<div
  class="date-dropdown-container"
  bind:this={dropdownRef}
  onclick={toggleDropdown}
  onkeydown={handleTriggerKeydown}
  role="button"
  tabindex="0"
>
  <img src="/calendar-icon.svg" alt="calendar" class="calendar-icon" />

  <div class="custom-dropdown">
    <div
      class="dropdown-trigger"
      aria-haspopup="listbox"
      aria-expanded={isOpen}
      role="button"
      tabindex="0"
      onkeydown={handleTriggerKeydown}
    >
      {formatDateForDropdown(currentDate, lang)}
    </div>

    {#if isOpen}
      <div class="dropdown-menu" role="listbox">
        {#each enabledDates as date}
          <button
            class="dropdown-item"
            class:selected={date === currentDate}
            onclick={(event) => selectDate(date, event)}
            role="option"
            aria-selected={date === currentDate}
          >
            {formatDateForDropdown(date, lang)}
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .date-dropdown-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    margin-bottom: 1rem;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s ease;
  }

  .date-dropdown-container:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  .date-label {
    font-size: 0.8rem;
    color: #666;
    margin: 0;
  }

  .custom-dropdown {
    position: relative;
  }

  .dropdown-trigger {
    font-size: 0.8rem;
    color: #666;
    background: none;
    border: none;
    cursor: pointer;
    font-family: inherit;
    padding: 0;
    margin: 0;
    outline: none;
    text-align: left;
    user-select: none;
  }

  .dropdown-trigger:hover {
    color: #333;
  }

  .dropdown-trigger:focus {
    outline: none;
  }

  .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: white;
    border: 1px solid #ddd;
    border-radius: 0.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    max-height: 200px;
    overflow-y: auto;
    min-width: 200px;
  }

  .dropdown-item {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    font-family: inherit;
    color: #333;
    background: white;
    border: none;
    cursor: pointer;
    text-align: left;
    border-radius: 0;
  }

  .dropdown-item:hover {
    background: #f5f5f5;
    color: #000;
  }

  .dropdown-item.selected {
    background: #0087ff;
    color: white;
  }

  .dropdown-item:first-child {
    border-top-left-radius: 0.5rem;
    border-top-right-radius: 0.5rem;
  }

  .dropdown-item:last-child {
    border-bottom-left-radius: 0.5rem;
    border-bottom-right-radius: 0.5rem;
  }

  .calendar-icon {
    width: 1rem;
    height: 1rem;
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .date-dropdown-container:hover {
      background-color: rgba(255, 255, 255, 0.05);
    }

    .date-label {
      color: #ccc;
    }

    .dropdown-trigger {
      color: #ccc;
    }

    .dropdown-trigger:hover {
      color: #ffffff;
    }

    .dropdown-menu {
      background: #2a2a2a;
      border-color: #404040;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .dropdown-item {
      background: #2a2a2a;
      color: #ffffff;
    }

    .dropdown-item:hover {
      background: #404040;
      color: #ffffff;
    }

    .dropdown-item.selected {
      background: #0087ff;
      color: white;
    }

    .calendar-icon {
      filter: brightness(0) invert(1);
    }
  }
</style>
