import React, { useState, useEffect } from 'react';
import { auth } from '../lib/supabase';

const UserProfile = ({ user, onSignOut }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="user-profile">
      <button 
        className="profile-btn"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="profile-avatar">
          {user.email.charAt(0).toUpperCase()}
        </div>
        <span className="profile-email">{user.email}</span>
        <span className="profile-arrow">{isOpen ? '▲' : '▼'}</span>
      </button>
      
      {isOpen && (
        <div className="profile-dropdown">
          <div className="profile-info">
            <div className="profile-detail">
              <strong>Email:</strong> {user.email}
            </div>
            <div className="profile-detail">
              <strong>Регистрация:</strong> {new Date(user.created_at).toLocaleDateString('ru-RU')}
            </div>
          </div>
          <button 
            onClick={onSignOut}
            className="sign-out-btn"
          >
            🚪 Выйти
          </button>
        </div>
      )}
    </div>
  );
};

export default UserProfile;