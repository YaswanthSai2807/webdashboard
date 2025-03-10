async function register() {
    const username = document.getElementById("register-username").value;
    const password = document.getElementById("register-password").value;
    const role = document.getElementById("register-role").value;

    const res = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role }),
    });

    const data = await res.json();
    alert(data.message || data.error);
}

async function login() {
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });

    const data = await res.json();
    if (data.token) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("role", data.role);
        window.location.href = "/dashboard";
    } else {
        alert("Invalid credentials");
    }
}

async function logout() {
    localStorage.removeItem("token");
    window.location.href = "/";
}

// document.addEventListener("DOMContentLoaded", async () => {
//     if (window.location.pathname === "/dashboard") {
//         document.getElementById("dashboard-message").innerText = `Welcome to the ${localStorage.getItem("role")} dashboard`;
//     }
// });
// Fetch user session data
async function getUserInfo() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html"; // Redirect to login if not authenticated
        return;
    }

    const response = await fetch("/api/user", {
        method: "GET",
        credentials: "include",  // Include session cookies
    });

    const data = await response.json();

    if (response.ok) {
        console.log("User ID:", data.user_id);
        console.log("Username:", data.username);
        console.log("Role:", data.role);
    } else {
        alert(data.error);
        localStorage.removeItem("token"); // Remove invalid token
        window.location.href = "login.html"; // Redirect to login
    }
}
setTimeout(function() {
    let alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => alert.style.display = "none");
  }, 3000);