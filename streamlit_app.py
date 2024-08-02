import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# --- App Title and Description ---
st.title("Thermostat Simulation: Comparing Control Algorithms")
st.write("This interactive simulation compares On-Off, PID, and Q-Learning control algorithms for maintaining room temperature.")

# --- File Uploader ---
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)  # Veri setinizi yükleyin
    outdoor_temp_values = df['Outdoor Temp (C)'].values
else:
    st.error("Please upload a CSV file to proceed.")
    st.stop()

# --- Input Parameters ---
st.sidebar.header("Simulation Parameters")
initial_room_temperature = st.sidebar.number_input("Initial Room Temperature (°C)", min_value=10, max_value=30, value=19)
thermostat_setting = st.sidebar.number_input("Thermostat Setting (°C)", min_value=15, max_value=25, value=20)
heater_power = st.sidebar.slider("Heater Power (°C/minute)", min_value=0.1, max_value=0.5, value=0.3)
base_heat_loss = st.sidebar.slider("Base Heat Loss (°C/minute)", min_value=0.05, max_value=0.2, value=0.1)
simulation_minutes = st.sidebar.number_input("Simulation Minutes", min_value=10, max_value=120, value=60)
thermostat_sensitivity = st.sidebar.slider("Thermostat Sensitivity (°C)", min_value=0.1, max_value=0.5, value=0.5, step=0.1)

# --- Q-Learning Parameters ---
st.sidebar.subheader("Q-Learning Parameters")
episodes = st.sidebar.number_input("Training Episodes", min_value=100, max_value=5000, value=1000)
learning_rate = 0.1  # Fixed for simplicity
discount_factor = 0.95  # Fixed for simplicity
exploration_rate = 0.1  # Fixed for simplicity

# --- PID Parameters ---
st.sidebar.subheader("PID Parameters")
Kp = st.sidebar.slider("Kp (Proportional Gain)", min_value=0.1, max_value=7.00, value=7.00)
Ki = st.sidebar.slider("Ki (Integral Gain)", min_value=0.01, max_value=0.7, value=0.05)
Kd = st.sidebar.slider("Kd (Derivative Gain)", min_value=0.001, max_value=0.2, value=0.01)

# --- Global Variables ---
num_states = 41
num_actions = 2
q_table = np.zeros((num_states, num_actions))  # Initialize q_table here

# --- Helper Functions ---
def get_state(temperature):
    """Discretizes the temperature into states."""
    return int(min(40, max(0, (temperature - 10) / 0.5)))

def get_action(state, q_table, exploration_rate):
    """Chooses an action based on the epsilon-greedy policy."""
    if np.random.uniform(0, 1) < exploration_rate:
        return np.random.choice(num_actions)  # Exploration
    else:
        return np.argmax(q_table[state, :])  # Exploitation

def get_reward(state, action, thermostat_setting):
    """Calculates the reward based on the state and action."""
    state_temp = 10 + state * 0.5
    if abs(state_temp - thermostat_setting) <= 0.5:
        return 10  # Within acceptable range
    elif action == 1 and state_temp > thermostat_setting + 0.5:  # Too hot
        return -10
    elif action == 0 and state_temp < thermostat_setting - 0.5:  # Too cold
        return -5
    else:
        return -1  # Slight penalty for not being in range

def get_outdoor_temp(minute, outdoor_temp_values):
    """Gets the outdoor temperature for the current minute."""
    index = int(minute // 5)  # Her 5 dakikada bir güncelle
    return outdoor_temp_values[min(index, len(outdoor_temp_values) - 1)]

# --- Simulation Logic (On-Off) ---
def run_on_off_simulation(initial_room_temperature, thermostat_sensitivity):
    time = []
    room_temperatures = []
    room_temperature = initial_room_temperature
    heater_status = False

    for minute in np.arange(0, simulation_minutes, 0.1):
        time.append(minute)
        outside_temperature = get_outdoor_temp(minute, outdoor_temp_values)

        if room_temperature < thermostat_setting - thermostat_sensitivity:
            heater_status = True
        elif room_temperature > thermostat_setting + thermostat_sensitivity:
            heater_status = False

        heat_loss = base_heat_loss * (room_temperature - outside_temperature) / 10

        if heater_status:
            room_temperature += heater_power * 0.1
        else:
            room_temperature -= heat_loss * 0.1

        room_temperatures.append(room_temperature)

    area_on_off = calculate_area_between_temp(time, room_temperatures, thermostat_setting)
    return time, room_temperatures, area_on_off  # Return area_on_off

# --- Simulation Logic (Q-Learning) ---
def run_q_learning_simulation(initial_room_temperature, thermostat_sensitivity):
    global q_table  # Ensure we're using the global q_table
    for episode in range(episodes):
        room_temperature = initial_room_temperature
        state = get_state(room_temperature)
        for minute in np.arange(0, simulation_minutes, 0.1):
            outside_temperature = get_outdoor_temp(minute, outdoor_temp_values)  # Add this line to get outdoor temperature
            action = get_action(state, q_table, exploration_rate)
            if action == 1:
                room_temperature += heater_power * 0.1
            else:
                heat_loss = base_heat_loss * (room_temperature - outside_temperature) / 10
                room_temperature -= heat_loss * 0.1

            next_state = get_state(room_temperature)
            reward = get_reward(next_state, action, thermostat_setting)

            q_table[state, action] += learning_rate * (reward + discount_factor * np.max(q_table[next_state, :]) - q_table[state, action])
            state = next_state

    # Run one final simulation using the learned Q-table
    time = []
    room_temperatures = []

    room_temperature = initial_room_temperature
    state = get_state(room_temperature)
    for minute in np.arange(0, simulation_minutes, 0.1):
        outside_temperature = get_outdoor_temp(minute, outdoor_temp_values)  # Add this line to get outdoor temperature
        action = np.argmax(q_table[state, :])  # Always choose the best action

        if action == 1:
            room_temperature += heater_power * 0.1
        else:
            heat_loss = base_heat_loss * (room_temperature - outside_temperature) / 10
            room_temperature -= heat_loss * 0.1

        state = get_state(room_temperature)
        time.append(minute)
        room_temperatures.append(room_temperature)

    area_q = calculate_area_between_temp(time, room_temperatures, thermostat_setting)
    return time, room_temperatures, area_q  # Return area_q

# --- Simulation Logic (PID) ---
def run_pid_simulation(initial_room_temperature, thermostat_sensitivity):
    time = []
    room_temperatures = []
    heater_output = []

    integral_error = 0
    previous_error = 0
    room_temperature = initial_room_temperature

    for minute in np.arange(0, simulation_minutes, 0.1):
        time.append(minute)
        outside_temperature = get_outdoor_temp(minute, outdoor_temp_values)

        error = thermostat_setting - room_temperature
        proportional_term = Kp * error
        integral_error += error * 0.1
        integral_term = Ki * integral_error
        derivative_term = Kd * (error - previous_error) / 0.1
        previous_error = error

        pid_output = proportional_term + integral_term + derivative_term
        pid_output = max(0, min(pid_output, 1))  # PID çıkışını sınırla
        heater_output.append(pid_output)

        heat_loss = base_heat_loss * (room_temperature - outside_temperature) / 10

        room_temperature += (heater_power * pid_output - heat_loss) * 0.1
        room_temperatures.append(room_temperature)

    area_pid = calculate_area_between_temp(time, room_temperatures, thermostat_setting)
    return time, room_temperatures, area_pid  # Return area_pid

# --- Calculate Area Between Current Temperature and Set Temperature ---
def calculate_area_between_temp(time, room_temperatures, set_temp):
    area = 0
    for i in range(1, len(time)):
        dt = time[i] - time[i - 1]
        avg_temp = (room_temperatures[i] + room_temperatures[i - 1]) / 2
        area += abs(avg_temp - set_temp) * dt
    return area

# --- Calculate Overshoot and Undershoot Metrics ---
def calculate_area_metrics(time, room_temperatures, set_temp):
    overshoot = 0
    undershoot = 0
    for i in range(1, len(time)):
        dt = time[i] - time[i - 1]
        avg_temp = (room_temperatures[i] + room_temperatures[i - 1]) / 2
        if avg_temp > set_temp:
            overshoot += (avg_temp - set_temp) * dt
        elif avg_temp < set_temp:
            undershoot += (set_temp - avg_temp) * dt
    return overshoot, undershoot

# --- Main Execution ---
if st.button("Run Simulations"):
    # On-Off Simulation
    time_on_off, room_temperatures_on_off, area_on_off = run_on_off_simulation(initial_room_temperature, thermostat_sensitivity)
    overshoot_on_off, undershoot_on_off = calculate_area_metrics(time_on_off, room_temperatures_on_off, thermostat_setting)

    # Q-Learning Simulation
    time_q, room_temperatures_q, area_q = run_q_learning_simulation(initial_room_temperature, thermostat_sensitivity)
    overshoot_q, undershoot_q = calculate_area_metrics(time_q, room_temperatures_q, thermostat_setting)

    # PID Simulation
    time_pid, room_temperatures_pid, area_pid = run_pid_simulation(initial_room_temperature, thermostat_sensitivity)
    overshoot_pid, undershoot_pid = calculate_area_metrics(time_pid, room_temperatures_pid, thermostat_setting)

    # Plotting
    fig, ax = plt.subplots()
    ax.plot(time_on_off, room_temperatures_on_off, label="On-Off Control")
    ax.plot(time_q, room_temperatures_q, label="Q-Learning Control")
    ax.plot(time_pid, room_temperatures_pid, label="PID Control")
    ax.axhline(y=thermostat_setting, color='r', linestyle='--', label="Thermostat Setting")
    ax.set_xlabel("Time (minutes)")
    ax.set_ylabel("Room Temperature (°C)")
    ax.legend()
    st.pyplot(fig)

    # Display Area Metrics
    st.subheader("Performance Metrics")
    st.write(f"On-Off Control - Area: {area_on_off:.2f}, Overshoot: {overshoot_on_off:.2f}, Undershoot: {undershoot_on_off:.2f}")
    st.write(f"Q-Learning Control - Area: {area_q:.2f}, Overshoot: {overshoot_q:.2f}, Undershoot: {undershoot_q:.2f}")
    st.write(f"PID Control - Area: {area_pid:.2f}, Overshoot: {overshoot_pid:.2f}, Undershoot: {undershoot_pid:.2f}")

    # Additional Plots for Overshoot and Undershoot
    fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Overshoot Plot
    ax1.bar(["On-Off Control", "Q-Learning Control", "PID Control"], [overshoot_on_off, overshoot_q, overshoot_pid], color=['blue', 'green', 'orange'])
    ax1.set_title('Overshoot Comparison')
    ax1.set_ylabel('Overshoot Area')

    # Undershoot Plot
    ax2.bar(["On-Off Control", "Q-Learning Control", "PID Control"], [undershoot_on_off, undershoot_q, undershoot_pid], color=['blue', 'green', 'orange'])
    ax2.set_title('Undershoot Comparison')
    ax2.set_ylabel('Undershoot Area')

    st.pyplot(fig2)

    # Outdoor Temperature Plot
    outdoor_time = np.arange(0, simulation_minutes, 5)
    outdoor_temps = [get_outdoor_temp(minute, outdoor_temp_values) for minute in outdoor_time]
    fig3, ax3 = plt.subplots()
    ax3.plot(outdoor_time, outdoor_temps, label="Outdoor Temperature", color='purple')
    ax3.set_xlabel("Time (minutes)")
    ax3.set_ylabel("Outdoor Temperature (°C)")
    ax3.legend()
    st.pyplot(fig3)
