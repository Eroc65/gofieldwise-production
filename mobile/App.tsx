import React from 'react';
import { SafeAreaView, Text, View } from 'react-native';

import { APP_NAME, MOBILE_API_BASE_URL } from './src/config';

export default function App(): JSX.Element {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#f5f7fa' }}>
      <View style={{ padding: 24, gap: 12 }}>
        <Text style={{ fontSize: 28, fontWeight: '700', color: '#0f172a' }}>{APP_NAME}</Text>
        <Text style={{ fontSize: 16, color: '#334155' }}>
          Native mobile starter is active. API base: {MOBILE_API_BASE_URL}
        </Text>
      </View>
    </SafeAreaView>
  );
}
