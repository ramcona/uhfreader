let eventSource;

// Connect to the server-sent events stream
function connectStream() {
  eventSource = new EventSource("/stream");
  eventSource.onmessage = function (e) {
    const data = JSON.parse(e.data);
    updateTable(data.data);
    updateStats(data.stats);
    updateButtons(data.is_running);
  };
}

// Fetch and populate serial ports
async function fetchPorts() {
  const response = await fetch("/get_ports");
  const ports = await response.json();
  const portSelect = document.getElementById("serial_port");
  portSelect.innerHTML = ports
    .map(
      (port) => `
        <option value="${port.device}" data-status="${port.status}">
            ${port.device} - ${port.description}
        </option>
    `
    )
    .join("");
  updatePortStatus(); // Update status label after populating ports
}

// Update port status label
function updatePortStatus() {
  const portSelect = document.getElementById("serial_port");
  const portStatus = document.getElementById("port_status");
  const selectedOption = portSelect.options[portSelect.selectedIndex];
  const status = selectedOption.getAttribute("data-status");
  portStatus.textContent = status;
  portStatus.style.color = status === "Connected" ? "green" : "red";
}

// Update the data table
function updateTable(data) {
  const table = document.getElementById("dataTable");
  table.innerHTML = `
                <tr>
                    <th>Timestamp</th>
                    <th>EPC</th>
                    <th>RSSI</th>
                    <th>Antenna</th>
                </tr>
                ${data
                  .map(
                    (row) => `
                    <tr>
                        <td>${row.timestamp}</td>
                        <td>${row.epc}</td>
                        <td>${row.rssi}</td>
                        <td>${row.antenna}</td>
                    </tr>
                `
                  )
                  .join("")}
            `;
}

// Update statistics
function updateStats(stats) {
  document.getElementById("totalReads").textContent = stats.total_reads;
  document.getElementById("lastRead").textContent = stats.last_read;
}

// Update button states
function updateButtons(isRunning) {
  const startButton = document.getElementById("startButton");
  const stopButton = document.getElementById("stopButton");
  if (isRunning) {
    startButton.disabled = true;
    stopButton.disabled = false;
  } else {
    startButton.disabled = false;
    stopButton.disabled = true;
  }
}

// Update settings
async function updateSettings(e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const response = await fetch("/update_settings", {
    method: "POST",
    body: formData,
  });
  const result = await response.json();
  alert(result.message);
}

// Start the RFID reader
async function startReader() {
  const response = await fetch("/start_reader");
  const result = await response.json();
  alert(result.message);
}

// Stop the RFID reader
async function stopReader() {
  const response = await fetch("/stop_reader");
  const result = await response.json();
  alert(result.message);
}

// Clear data
async function clearData() {
  const response = await fetch("/clear_data");
  const result = await response.json();
  alert(result.message);
  location.reload();
}

// Import participant data
async function importParticipants(e) {
  e.preventDefault();
  const formData = new FormData();
  formData.append("file", e.target.file.files[0]);
  const response = await fetch("/import_participants", {
    method: "POST",
    body: formData,
  });
  const result = await response.json();
  alert(result.message);
  fetchParticipants(); // Refresh participant list after import
}

// Fetch and display participant data
async function fetchParticipants() {
  try {
    const response = await fetch("/get_participants");
    const result = await response.json();
    if (result.success) {
      updateParticipantTable(result.data);
    } else {
      alert(`Error: ${result.message}`);
    }
  } catch (error) {
    alert("Failed to fetch participants. Please try again.");
  }
}

// Update the participant table
function updateParticipantTable(data) {
  const tableBody = document.querySelector("#participantTable tbody");
  tableBody.innerHTML = data
    .map(
      (participant) => `
                <tr>
                    <td>${participant["Member NO"]}</td>
                    <td>${participant["Nama"]}</td>
                    <td>${participant["Alamat"]}</td>
                    <td>${participant["Gender"]}</td>
                    <td>${participant["EPC"]}</td>
                    <td>${participant["Country"]}</td>
                    <td>${participant["Status"]}</td>
                </tr>
            `
    )
    .join("");
}

// Open a specific tab
function openTab(tabName) {
  const tabs = document.querySelectorAll(".tab-content");
  tabs.forEach((tab) => (tab.style.display = "none"));
  document.getElementById(tabName).style.display = "block";

  if (tabName === "participants") {
    fetchParticipants(); // Fetch and display participants
  }
}

// Initialize the page
window.onload = function () {
  connectStream();
  fetchPorts();
  openTab("start"); // Default tab
};
