import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import axios from 'axios';
import { API_CONFIG } from '../config';

interface OrganizedGroup {
  zone: string;
  items: string[];
}

export default function ShoppingList() {
  const { items, store_id, store_name } = useLocalSearchParams();
  const [organizedList, setOrganizedList] = useState<OrganizedGroup[]>([]);
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    organizeItems();
  }, []);

  const organizeItems = async () => {
    try {
      const itemList = typeof items === 'string' ? items.split(',').map(item => item.trim()) : [];
      const storeId = typeof store_id === 'string' ? parseInt(store_id) : 1;
      
      console.log('Making request to:', `${API_CONFIG.BASE_URL}/organize`);
      console.log('Request data:', { items: itemList, store_id: storeId });
      
      const response = await axios.post(`${API_CONFIG.BASE_URL}/organize`, {
        items: itemList,
        store_id: storeId
      });
      
      setOrganizedList(response.data.content);
    } catch (err) {
      console.error('API Error:', err);
      setError(`Failed to organize items. Make sure your backend is running on ${API_CONFIG.BASE_URL}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (item: string) => {
    const newCheckedItems = new Set(checkedItems);
    if (newCheckedItems.has(item)) {
      newCheckedItems.delete(item);
    } else {
      newCheckedItems.add(item);
    }
    setCheckedItems(newCheckedItems);
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2e7d32" />
        <Text style={styles.loadingText}>Organizing your list...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Your Shopping List</Text>
      {store_name && (
        <Text style={styles.storeName}>📍 {store_name}</Text>
      )}
      
      {/* Active groups first */}
      {organizedList
        .filter(group => !group.items.every(item => checkedItems.has(item)))
        .map((group, index) => {
          const isCompleted = group.items.every(item => checkedItems.has(item));
          return (
            <View key={index} style={[styles.section, isCompleted && styles.completedSection]}>
              <Text style={[styles.sectionTitle, isCompleted && styles.completedSectionTitle]}>
                {group.zone}
              </Text>
              {group.items.map((item, itemIndex) => {
                const isChecked = checkedItems.has(item);
                return (
                  <TouchableOpacity 
                    key={itemIndex} 
                    style={styles.itemContainer}
                    onPress={() => toggleItem(item)}
                  >
                    <Text style={styles.checkbox}>
                      {isChecked ? '☑️' : '☐'}
                    </Text>
                    <Text style={[
                      styles.item,
                      isChecked && styles.checkedItem
                    ]}>
                      {item}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          );
        })}

      {/* Completed groups at bottom */}
      {organizedList
        .filter(group => group.items.every(item => checkedItems.has(item)))
        .map((group, index) => {
          const isCompleted = group.items.every(item => checkedItems.has(item));
          return (
            <View key={`completed-${index}`} style={[styles.section, styles.completedSection]}>
              <Text style={[styles.sectionTitle, styles.completedSectionTitle]}>
                {group.zone}
              </Text>
              {group.items.map((item, itemIndex) => {
                const isChecked = checkedItems.has(item);
                return (
                  <TouchableOpacity 
                    key={itemIndex} 
                    style={styles.itemContainer}
                    onPress={() => toggleItem(item)}
                  >
                    <Text style={styles.checkbox}>
                      {isChecked ? '☑️' : '☐'}
                    </Text>
                    <Text style={[
                      styles.item,
                      isChecked && styles.checkedItem
                    ]}>
                      {item}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          );
        })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 20,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#2e7d32',
    textAlign: 'center',
  },
  storeName: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
  },
  section: {
    marginBottom: 20,
    backgroundColor: '#f5f5f5',
    padding: 15,
    borderRadius: 8,
  },
  completedSection: {
    backgroundColor: '#e8e8e8',
    opacity: 0.7,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#2e7d32',
  },
  completedSectionTitle: {
    textDecorationLine: 'line-through',
    color: '#999',
  },
  itemContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    paddingVertical: 4,
  },
  checkbox: {
    fontSize: 18,
    marginRight: 10,
    width: 25,
  },
  item: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  checkedItem: {
    textDecorationLine: 'line-through',
    color: '#999',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  errorText: {
    fontSize: 16,
    color: '#d32f2f',
    textAlign: 'center',
    padding: 20,
  },
});
