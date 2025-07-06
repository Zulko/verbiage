<script>
  import { createEventDispatcher } from "svelte";
  import { DatePicker } from "@svelte-plugins/datepicker";

  let {
    isOpen = $bindable(),
    enabledDates,
    date = $bindable(),
    lang,
  } = $props();
  const dispatch = createEventDispatcher();

  // Convert date strings to Date objects for the datepicker
  // Local state for the picker
  let selectedDate = $state(new Date());

  $effect(() => {
    if (date) {
      const [year, month, day] = date.split("-").map((n) => parseInt(n, 10));
      const newDate = new Date(year, month - 1, day);
      selectedDate = newDate;
    } else {
      selectedDate = new Date();
    }
  });

  function handleDateChange(evt) {
    const pickedDate = new Date(evt.startDate);
    const month = (pickedDate.getMonth() + 1).toString().padStart(2, "0");
    const day = pickedDate.getDate().toString().padStart(2, "0");
    date = `${pickedDate.getFullYear()}-${month}-${day}`;
    isOpen = false;
  }
</script>

{#if isOpen}
  <div class="calendar-wrapper">
    <DatePicker
      {isOpen}
      startDate={date.replace(/-/g, "/")}
      enabledDates={enabledDates.map((date) => date.replace("-", "/"))}
      onDayClick={handleDateChange}
    >
      <input type="text" style="display: none;" readonly value="" />
    </DatePicker>
  </div>
{/if}

<style>
  .calendar-wrapper {
    width: 100%;
    display: flex;
    justify-content: center;
  }
  :global(.calendar-wrapper .calendars-container) {
    transform: translateX(-50%) !important;
  }

  /* Dark mode support for DatePicker */
  @media (prefers-color-scheme: dark) {
    :global(.datepicker) {
      /* Container styling */
      --datepicker-container-background: #1a1a1a;
      --datepicker-container-border: 1px solid #404040;
      --datepicker-container-box-shadow: 0 1px 20px rgba(0, 0, 0, 0.3);

      /* General text and colors */
      --datepicker-color: #ffffff;
      --datepicker-border-color: #404040;

      /* Calendar background */
      --datepicker-calendar-background: #1a1a1a;

      /* Calendar header */
      --datepicker-calendar-header-text-color: #ffffff;
      --datepicker-calendar-header-month-nav-background-hover: #333333;
      --datepicker-calendar-header-month-nav-color: #ffffff;
      --datepicker-calendar-header-month-nav-icon-next-filter: invert(1);
      --datepicker-calendar-header-month-nav-icon-prev-filter: invert(1);
      --datepicker-calendar-header-year-nav-color: #ffffff;
      --datepicker-calendar-header-year-nav-icon-next-filter: invert(1);
      --datepicker-calendar-header-year-nav-icon-prev-filter: invert(1);

      /* Days of week */
      --datepicker-calendar-dow-color: #a0a0a0;

      /* Calendar days */
      --datepicker-calendar-day-color: #ffffff;
      --datepicker-calendar-day-color-disabled: #666666;
      --datepicker-calendar-day-background-hover: #333333;
      --datepicker-calendar-day-color-hover: #ffffff;

      /* Calendar days outside of current month */
      --datepicker-calendar-day-other-color: #666666;

      /* Today's date */
      --datepicker-calendar-today-border: 1px solid #ffffff;
      --datepicker-calendar-today-background: transparent;

      /* Active/selected states */
      --datepicker-state-active: #0087ff;
      --datepicker-state-hover: #333333;

      /* Range selection (if used) */
      --datepicker-calendar-range-background: #333333;
      --datepicker-calendar-range-selected-background: #0087ff;
      --datepicker-calendar-range-selected-color: #ffffff;

      /* Split border between calendars (if multipane) */
      --datepicker-calendar-split-border: 1px solid #404040;

      /* Presets (if used) */
      --datepicker-presets-border: 1px solid #404040;
      --datepicker-presets-button-color: #ffffff;
      --datepicker-presets-button-background-hover: #333333;
      --datepicker-presets-button-background-active: #0087ff;
      --datepicker-presets-button-color-active: #ffffff;

      /* Time picker (if used) */
      --datepicker-timepicker-input-border: 1px solid #404040;
      --datepicker-timepicker-input-background: #2a2a2a;
      --datepicker-timepicker-input-color: #ffffff;
    }
  }
</style>
