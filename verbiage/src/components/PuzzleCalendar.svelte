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
</style>
