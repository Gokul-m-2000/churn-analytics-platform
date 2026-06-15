# AI-Powered Customer Churn Prediction and Retention System

## Overview

This project is an end-to-end customer churn prediction platform designed to help telecom companies identify customers who are likely to discontinue their services and take proactive retention actions.

The system combines Machine Learning, Explainable AI, FastAPI, SQLAlchemy, SQLite, and an interactive dashboard into a single application. In addition to predicting churn risk, the platform explains why a customer is likely to churn and generates personalized retention recommendations.

---

## Key Features

* Customer churn prediction using XGBoost
* Explainable AI using SHAP
* Custom feature engineering pipeline
* Customer risk scoring and classification
* AI-powered retention recommendations
* FastAPI REST API backend
* SQLite database integration
* SQLAlchemy ORM
* Role-based authentication and authorization
* Customer What-If Simulator
* Prediction update pipeline
* Interactive dashboard

---

## Dataset

The model was trained using the Telco Customer Churn Dataset.

The dataset contains:

* Customer demographics
* Subscription details
* Service usage information
* Billing information
* Contract details
* Churn labels

Example features include:

* Gender
* Senior Citizen
* Partner
* Dependents
* Internet Service
* Online Security
* Online Backup
* Device Protection
* Tech Support
* Streaming Services
* Monthly Charges
* Total Charges
* Contract Type
* Payment Method
* Tenure

---

## Data Preprocessing

The following preprocessing steps were applied before model training:

### Data Cleaning

* Converted `TotalCharges` to numeric format
* Removed invalid and missing values

### Encoding

Categorical variables were transformed into numerical representations suitable for machine learning models.

### Feature Scaling

Numerical features were scaled using `StandardScaler`.

Scaled features include:

* Tenure
* Monthly Charges
* Total Charges

The trained scaler is saved and reused during inference to ensure consistency between training and prediction environments.

---

## Feature Engineering

To improve model performance, two custom features were created.

### PremiumServicesCount

Counts the number of premium services subscribed by a customer.

Included services:

* Online Security
* Online Backup
* Device Protection
* Tech Support
* Streaming TV
* Streaming Movies

This feature helps measure customer engagement.

### HasSecurityBundle

A binary feature indicating whether a customer subscribes to both:

* Online Security
* Online Backup

This helps capture customer investment in security-related services.

---

## Machine Learning Model

The churn prediction engine uses **XGBoost Classifier**.

### Why XGBoost?

* Strong performance on structured/tabular data
* High predictive accuracy
* Handles feature interactions effectively
* Supports feature importance analysis
* Efficient training and inference

### Tuned Hyperparameters

* n_estimators = 200
* max_depth = 6
* learning_rate = 0.05
* scale_pos_weight = 3

---

## Model Performance

### Classification Report

| Metric    | Non-Churn (0) | Churn (1) |
| --------- | ------------- | --------- |
| Precision | 0.89          | 0.50      |
| Recall    | 0.72          | 0.75      |
| F1-Score  | 0.80          | 0.60      |

### Overall Metrics

| Metric            | Score |
| ----------------- | ----- |
| Accuracy          | 0.73  |
| Weighted F1 Score | 0.74  |
| Macro F1 Score    | 0.70  |

### Interpretation

The model is designed to identify churn customers effectively.

Although churn customers represent the minority class, the model achieves:

* 75% Recall for churn customers
* 60% F1-Score for churn customers

This helps reduce the number of high-risk customers that go undetected while maintaining reasonable overall performance.

---

## Explainable AI

The project uses both **XGBoost Feature Importance** and **SHAP**.

### XGBoost Feature Importance

Provides a global view of which features are most influential across the entire model.

### SHAP Explanations

SHAP is used to generate customer-specific churn drivers.

The prediction pipeline uses `SHAP TreeExplainer` to identify the factors contributing most to a customer's churn risk.

These churn drivers are:

* Stored in the database
* Displayed on the dashboard
* Used to help business users understand individual predictions

---

## LLM-generated retention recommendations

After generating churn predictions, customer information and prediction insights are sent to the Groq API.

The language model generates personalized retention recommendations based on the customer's profile and churn risk.

Example recommendations:

* Contract upgrade suggestions
* Loyalty incentives
* Technical support offers
* Service bundle recommendations

---

## Customer What-If Simulator

The simulator allows users to modify customer attributes and instantly observe how churn risk changes.

### Simulator Workflow

1. Load the selected customer's existing data.
2. Update only the fields modified by the user.
3. Recalculate derived values such as Total Charges.
4. Recreate engineered features:

   * PremiumServicesCount
   * HasSecurityBundle
5. Apply the same preprocessing pipeline used during training.
6. Apply the saved StandardScaler.
7. Generate a new prediction using the trained XGBoost model.
8. Generate updated retention recommendations.

This ensures consistency between training and inference workflows.

---

## Database Design

The application uses SQLite with three primary tables.

### Users

Stores:

* Email
* Password Hash
* User Role

### Customers

Stores:

* Customer demographic information
* Service subscriptions
* Financial information
* Customer activity data

### Churn Predictions

Stores:

* Churn probability
* Risk level
* SHAP churn drivers
* Prediction timestamp

---

## Authentication and Authorization

The application implements role-based access control.

### Staff Users

Can:

* View dashboard
* View predictions
* Use simulator
* View recommendations

### Admin Users

Additional permissions:

* Run prediction update pipeline
* Promote staff users
* Demote administrators
* Manage user roles

Passwords are stored using bcrypt hashing.

---

## Prediction Update Pipeline

Administrators can trigger a prediction update pipeline from the dashboard.

### Pipeline Steps

1. Read customer data from the database.
2. Apply preprocessing.
3. Apply feature engineering.
4. Apply feature scaling.
5. Generate churn predictions.
6. Generate SHAP explanations.
7. Store prediction results in the database.

This keeps prediction records synchronized with customer data.

---

## Technology Stack

### Machine Learning

* Python
* XGBoost
* Scikit-Learn
* Pandas
* NumPy
* SHAP

### Backend

* FastAPI
* SQLAlchemy

### Database

* SQLite

### Frontend

* HTML
* JavaScript
* Tailwind CSS

---

## Project Architecture


Customer Data
      ↓
Feature Engineering
      ↓
Feature Scaling
      ↓
XGBoost Prediction
      ↓
SHAP Explanation
      ↓
Prediction Storage
      ↓
Groq Recommendation Generation
      ↓
Dashboard Visualization



---


