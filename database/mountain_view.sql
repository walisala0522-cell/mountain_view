-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Mar 06, 2026 at 05:43 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `mountain_view`
--

-- --------------------------------------------------------

--
-- Table structure for table `bookings`
--

CREATE TABLE `bookings` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `room_id` int(11) DEFAULT NULL,
  `check_in` date DEFAULT NULL,
  `check_out` date DEFAULT NULL,
  `actual_checkout_date` date DEFAULT NULL,
  `checkout_time` varchar(5) DEFAULT NULL,
  `status` enum('pending','approved','cancelled') DEFAULT 'pending',
  `customer_name` varchar(255) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `room_type` varchar(100) DEFAULT NULL,
  `guest_count` int(11) DEFAULT NULL,
  `room_count` int(11) DEFAULT NULL,
  `nights` int(11) DEFAULT NULL,
  `total_price` int(11) DEFAULT NULL,
  `payment_method` varchar(20) DEFAULT NULL,
  `payment_status` varchar(50) DEFAULT NULL,
  `slip_image` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `paid_at` timestamp NULL DEFAULT NULL,
  `verified_at` timestamp NULL DEFAULT NULL,
  `cancelled_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `bookings`
--

INSERT INTO `bookings` (`id`, `user_id`, `room_id`, `check_in`, `check_out`, `actual_checkout_date`, `checkout_time`, `status`, `customer_name`, `phone`, `room_type`, `guest_count`, `room_count`, `nights`, `total_price`, `payment_method`, `payment_status`, `slip_image`, `created_at`, `paid_at`, `verified_at`, `cancelled_at`) VALUES
(27, 5, 10, '2026-03-10', '2026-03-12', '2026-03-05', '20:19', 'pending', 'Ron Thai', '0999999999', NULL, 5, 1, NULL, 5000, 'qr', 'paid', 'cca3376b-14d7-4907-95bb-107fc43c7f02_631761174_941875144849500_1372320851972097433_n.jpg', '2026-03-04 07:35:10', '2026-03-04 07:35:35', NULL, NULL),
(28, 4, 7, '2026-03-16', '2026-03-18', '2026-03-04', '14:44', 'pending', 'Asron Dolo', '0864966943', NULL, 1, 1, NULL, 6000, 'cash', 'paid', NULL, '2026-03-04 07:39:40', '2026-03-04 07:39:53', NULL, NULL),
(29, 4, 5, '2026-03-04', '2026-03-05', '2026-03-04', '14:45', 'pending', 'Asron Dolo', '0864966943', NULL, 3, 1, NULL, 3000, 'qr', 'paid', '63cabe24-e4de-4e2d-b9c0-0d9a10a81964_Screenshot_2026-02-26_111129.png', '2026-03-04 07:44:39', '2026-03-04 07:44:49', NULL, NULL),
(30, 4, 5, '2026-03-04', '2026-03-05', '2026-03-04', '14:57', 'pending', 'Asron Dolo', '0864966943', NULL, 5, 1, NULL, 3000, 'qr', 'paid', '6154dc6b-06f5-4d82-9bbd-6a3104fa1bcd_631761174_941875144849500_1372320851972097433_n.jpg', '2026-03-04 07:56:13', '2026-03-04 07:57:21', NULL, NULL),
(31, 4, 7, '2026-03-19', '2026-03-20', '2026-03-05', '19:48', 'pending', 'Asron Dolo', '0864966943', NULL, 3, 1, NULL, 3000, 'qr', 'paid', '8ac15adb-bed4-44f3-acd0-a33447fde0b2_Screenshot_2026-02-26_111129.png', '2026-03-04 07:58:20', '2026-03-04 07:58:42', NULL, NULL),
(32, 3, 5, '2026-03-04', '2026-03-05', '2026-03-05', '19:47', 'pending', 'นาย ธัญชน จันทร์สำราญ', '0630848763', NULL, 1, 1, NULL, 3000, 'qr', 'paid', 'f9a55859-4d69-4e97-bc2a-fcf99846f798_slip.jpg', '2026-03-04 13:51:49', '2026-03-04 13:59:45', NULL, NULL),
(33, 2, 6, '2026-03-04', '2026-03-05', '2026-03-05', '20:18', 'pending', 'นางสุภัชญา บุตรสา', '0986894629', NULL, 2, 1, NULL, 2500, NULL, 'paid', NULL, '2026-03-04 14:23:39', '2026-03-05 12:48:16', NULL, NULL),
(34, 3, 5, '2026-03-05', '2026-03-06', '2026-03-05', '20:21', 'pending', 'นางอารียา จิตชำนาญ', '0929372462', NULL, 1, 1, NULL, 3000, 'qr', 'paid', 'c162836e-c5ee-42a5-b020-bf811b937802_slip.jpg', '2026-03-05 13:10:55', '2026-03-05 13:18:09', NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `facilities`
--

CREATE TABLE `facilities` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `icon_class` varchar(100) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `facilities`
--

INSERT INTO `facilities` (`id`, `name`, `icon_class`, `created_at`) VALUES
(1, 'Free Wi-Fi', 'fa-solid fa-wifi', '2026-02-28 11:41:01'),
(2, 'เครื่องปรับอากาศ', 'fa-solid fa-snowflake', '2026-02-28 11:41:01'),
(3, 'เครื่องทำน้ำอุ่น', 'fa-solid fa-shower', '2026-02-28 11:41:01'),
(4, 'ที่จอดรถ', 'fa-solid fa-square-parking', '2026-02-28 11:41:01'),
(5, 'ทีวี', 'fa-solid fa-tv', '2026-02-28 11:41:01'),
(6, 'ตู้เย็น', 'fa-solid fa-cube', '2026-02-28 11:41:01');

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE `rooms` (
  `id` int(11) NOT NULL,
  `room_name` varchar(100) NOT NULL,
  `status` enum('available','occupied') DEFAULT 'available',
  `price` int(11) DEFAULT 0,
  `room_type` varchar(50) DEFAULT NULL,
  `availability` varchar(20) DEFAULT 'available',
  `is_available` tinyint(1) DEFAULT 1,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `rooms`
--

INSERT INTO `rooms` (`id`, `room_name`, `status`, `price`, `room_type`, `availability`, `is_available`, `is_active`, `created_at`) VALUES
(5, 'ห้องแอร์ A1', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(6, 'ห้องพัดลม A2', 'available', 2500, 'พัดลม', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(7, 'ห้องแอร์ A3', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(8, 'ห้องพัดลม A4', 'available', 2500, 'พัดลม', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(9, 'ห้องแอร์ A5', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(10, 'ห้องพัดลม A6', 'available', 2500, 'พัดลม', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(11, 'ห้องแอร์ A7', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(12, 'ห้องพัดลม A8', 'available', 2500, 'พัดลม', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(13, 'ห้องแอร์ A9', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(14, 'ห้องพัดลม A10', 'available', 2500, 'พัดลม', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(15, 'ห้องแอร์ A11', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(16, 'ห้องพัดลม A12', 'available', 2500, 'พัดลม', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(17, 'ห้องแอร์ A13', 'available', 3000, 'แอร์', 'ว่าง', 1, 1, '2026-02-28 11:35:18'),
(18, 'ห้องพัดลม A14', 'available', 2500, NULL, 'available', 0, 0, '2026-03-05 12:49:39');

-- --------------------------------------------------------

--
-- Table structure for table `room_facilities`
--

CREATE TABLE `room_facilities` (
  `id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `facility_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_facilities`
--

INSERT INTO `room_facilities` (`id`, `room_id`, `facility_id`) VALUES
(1, 5, 1),
(2, 5, 2),
(3, 5, 3),
(4, 5, 4),
(5, 5, 5),
(6, 5, 6);

-- --------------------------------------------------------

--
-- Table structure for table `room_images`
--

CREATE TABLE `room_images` (
  `id` int(11) NOT NULL,
  `room_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('admin','user') DEFAULT 'user',
  `google_id` varchar(100) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `password`, `role`, `google_id`, `email`, `phone`, `created_at`) VALUES
(1, 'admin', '1234', 'admin', NULL, NULL, NULL, '2026-02-28 11:35:18'),
(2, 'Admin booking', 'google_login', 'admin', '105374397139270196724', 'mountainview.bungalow0522@gmail.com', '0986894629', '2026-02-28 11:35:18'),
(3, 'Warisara Somnuk', 'google_login', 'user', '110239236982877770013', 'walisala0522@gmail.com', '0630848763', '2026-02-28 11:35:18'),
(4, 'Asron Dolo', 'google_login', 'admin', '110631022972833241996', 'ronasron2546@gmail.com', '0864966943', '2026-02-28 11:35:18'),
(5, 'Ron Thai', '', '', '108733396230673380692', 'ronnegamer007@gmail.com', '0999999999', '2026-02-28 12:39:33');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `bookings`
--
ALTER TABLE `bookings`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `room_id` (`room_id`);

--
-- Indexes for table `facilities`
--
ALTER TABLE `facilities`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `rooms`
--
ALTER TABLE `rooms`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `room_facilities`
--
ALTER TABLE `room_facilities`
  ADD PRIMARY KEY (`id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `facility_id` (`facility_id`);

--
-- Indexes for table `room_images`
--
ALTER TABLE `room_images`
  ADD PRIMARY KEY (`id`),
  ADD KEY `room_id` (`room_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `bookings`
--
ALTER TABLE `bookings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=35;

--
-- AUTO_INCREMENT for table `facilities`
--
ALTER TABLE `facilities`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `rooms`
--
ALTER TABLE `rooms`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT for table `room_facilities`
--
ALTER TABLE `room_facilities`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `room_images`
--
ALTER TABLE `room_images`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `bookings`
--
ALTER TABLE `bookings`
  ADD CONSTRAINT `bookings_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `bookings_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`);

--
-- Constraints for table `room_facilities`
--
ALTER TABLE `room_facilities`
  ADD CONSTRAINT `room_facilities_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `room_facilities_ibfk_2` FOREIGN KEY (`facility_id`) REFERENCES `facilities` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `room_images`
--
ALTER TABLE `room_images`
  ADD CONSTRAINT `room_images_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
